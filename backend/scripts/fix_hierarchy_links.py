"""
Fix parent_position_id links to complete the position hierarchy chain.

Current state analysis:
  LT/SK -> OE              (1464 positions work)
  OE (format: OE@LOC) -> DM (96 OEs work)
  OE (format: OE-AP-... ) -> DM (86 OEs BROKEN - no parent)
  DM (DISTRICT-MANAGER-...) -> RM (BROKEN - no parent set for full-name DMs)
  DM (DM@LOC) -> RM (points to placeholder RMs w/o employees)
  RM with employees -> SPH (IDs 3, 136, 137, 138 have parent=5929)
  Placeholder RMs -> SPH (IDs 5900, 5901, 5922, 5928 BROKEN)

Fix plan:
  1. Point ALL DMs (both formats) to correct RM with employee (IDs 3,136,137,138)
  2. Point OEs without parent to same DM as their matching @format OE sibling
  3. Point placeholder RMs (5900,5901,5922,5928) to SPH
  4. Point generic OE-AP-104-MMU (ID=5933) to a default DM
"""
import asyncio
import sys
sys.path.insert(0, '.')
import re
from app.database import AsyncSessionLocal
from sqlalchemy import text


# RM mapping: Replace placeholder RM IDs with actual RMs that have employees
RM_PLACEHOLDER_TO_ACTUAL = {
    5900: 3,    # REGIONAL-AP-104-MMU-MANAGER-VIJAYAWADA -> RM@VIJAYWADA (Himaja Sai Vaani Ganta)
    5928: 136,  # REGIONAL-MANAGER-AP-104-MMU-ONGOLE -> REGIONAL MANAGER@ONGOLE (Kaleem Mohammed)
    5901: 137,  # REGIONAL-MANAGER-AP-104-MMU-VIZIANAGARAM -> RM@VIZIANAGARAM (Laxman Rao Allam)
    5922: 138,  # REGIONAL-MANAGER-AP-104-MMU-YSR-KADAPA -> REGIONAL MANAGER@YSR KADAPA (Shaik Ikbal Hussain)
}

# District -> RM ID mapping for DMs without parent
DISTRICT_TO_RM = {
    "NTR": 3, "KRISHNA": 3, "EAST GODAVARI": 3, "EAST-GODAVARI": 3,
    "KAKINADA": 3, "KONASEEMA": 3, "WEST GODAVARI": 3, "WEST-GODAVARI": 3,
    "ELURU": 3, "POLAVARAM": 3, "VISAKAPATNAM": 3,
    "ONGOLE": 136, "GUNTUR": 136, "BAPATLA": 136, "PALNADU": 136,
    "MARKAPURAM": 136, "PRAKASAM": 136, "SPSR NELLORE": 136, "SPSR-NELLORE": 136,
    "NELLORE": 136, "TIRUPATHI": 136,
    "VIZIANAGARAM": 137, "ANAKAPALLI": 137, "PARVATHIPURAM": 137,
    "SRIKAKULAM": 137, "VISAKHAPATNAM": 137, "ASR": 137,
    "YSR KADAPA": 138, "YSR-KADAPA": 138, "KADAPA": 138,
    "ANANTHAPUR": 138, "ANANTAPUR": 138, "ANNAMAYYA": 138,
    "CHITTO0R": 138, "CHITTOOR": 138, "KURNOOL": 138,
    "NANDYAL": 138, "NAGARI": 138, "SRI SATYA SAI": 138, "SRI-SATYA-SAI": 138,
}

SPH_ID = 5929  # SPH-AP-104-MMU


def extract_district(code: str) -> str:
    """Extract district/region name from a DM position code."""
    c = code.upper()
    for s in ["-AP-104-MMUS", "-AP-104-MMU"]:
        c = c.replace(s, "")
    
    if "@" in c:
        d = c.split("@")[1]
    elif "MANAGER-" in c:
        d = c.split("MANAGER-")[-1]
    else:
        parts = c.split("-")
        if len(parts) > 1:
            # DM-0001 -> NTR
            if parts[0] == "DM" and parts[1] == "0001":
                return "NTR"
            d = parts[-1]
        else:
            d = c
    
    # Clean up
    d = d.strip(" -_")
    # DISTRICTMANAGERKAKINADA -> KAKINADA (extract last meaningful part)
    if d.startswith("DISTRICTMANAGER"):
        d = d.replace("DISTRICTMANAGER", "")
    elif d == "DISTRICT":
        return ""
    return d


def find_rm_for_dm(district: str) -> int | None:
    """Find the correct RM ID for a given district name."""
    if not district:
        return None
    d_upper = district.upper().strip()
    for key, rm_id in DISTRICT_TO_RM.items():
        k_upper = key.upper()
        if k_upper in d_upper or d_upper in k_upper:
            return rm_id
    return None


async def fix():
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("STEP 1: FIX DM -> RM LINKS")
        print("=" * 60)
        
        # Get all DMs
        q = text("SELECT id, code, parent_position_id FROM positions WHERE role_name = 'DISTRICT MANAGER'")
        dms = (await db.execute(q)).all()
        
        fix1 = 0
        for dm in dms:
            district = extract_district(dm.code)
            target_rm = find_rm_for_dm(district)
            
            if target_rm and dm.parent_position_id != target_rm:
                old = dm.parent_position_id
                await db.execute(
                    text("UPDATE positions SET parent_position_id = :rm WHERE id = :dm"),
                    {"rm": target_rm, "dm": dm.id}
                )
                print(f"  DM ID={dm.id}: {dm.code} -> RM ID={target_rm} (was: {old})")
                fix1 += 1
            elif not target_rm:
                print(f"  DM ID={dm.id}: {dm.code} (district='{district}') - NO RM MATCH")
            elif dm.parent_position_id == target_rm:
                pass  # Already correct
        
        print(f"\nFixed {fix1} DM->RM links")
        await db.flush()
        
        print("\n" + "=" * 60)
        print("STEP 2: FIX OE -> DM LINKS")
        print("=" * 60)
        
        # Get all DMs
        q = text("SELECT id, code FROM positions WHERE role_name = 'DISTRICT MANAGER'")
        all_dms = (await db.execute(q)).all()
        
        # Build a map of OE location -> DM ID from OEs that already have parents
        q = text("""
            SELECT p.code, p.parent_position_id
            FROM positions p
            WHERE p.role_name = 'OE' AND p.parent_position_id IS NOT NULL
        """)
        linked_oes = (await db.execute(q)).all()
        
        loc_to_dm = {}
        for oe in linked_oes:
            c = oe.code.upper()
            # Extract location from OE code
            if "@" in c:
                if c.startswith("OE@"):
                    loc = c.split("@")[1]
                else:
                    loc = c.split("@")[0].replace("OE", "")
            else:
                loc = c.replace("OE-", "").replace("OE", "").strip("- ")
            # Take first part before dash
            loc = loc.split("-")[0].split(" ")[0].strip()
            if loc and len(loc) > 2:
                loc_to_dm[loc] = oe.parent_position_id
        
        # Get OEs without parent
        q = text("SELECT id, code FROM positions WHERE role_name = 'OE' AND parent_position_id IS NULL")
        unlinked_oes = (await db.execute(q)).all()
        print(f"OEs without parent: {len(unlinked_oes)}")
        
        fix2 = 0
        for oe in unlinked_oes:
            c = oe.code.upper()
            # Extract location
            if "@" in c:
                if c.startswith("OE@"):
                    loc = c.split("@")[1]
                else:
                    loc = c.split("@")[0].replace("OE", "")
            else:
                loc = c.replace("OE-", "").replace("OE", "").strip("- ")
            
            # Take first meaningful part
            loc_clean = loc.split("-")[0].split(" ")[0].strip()
            
            found = False
            
            # 1. Direct match from sibling OEs
            if loc_clean in loc_to_dm:
                dm_id = loc_to_dm[loc_clean]
                await db.execute(
                    text("UPDATE positions SET parent_position_id = :dm WHERE id = :oe"),
                    {"dm": dm_id, "oe": oe.id}
                )
                print(f"  {oe.code} -> DM ID={dm_id} (sibling match: {loc_clean})")
                fix2 += 1
                found = True
            
            # 2. Fuzzy match on DM district names
            if not found:
                best_dm = None
                best_score = 0
                for dm in all_dms:
                    dd = extract_district(dm.code).upper()
                    # Check matching
                    if loc_clean and dd:
                        if loc_clean == dd:
                            score = 1.0
                        elif len(loc_clean) >= 4 and dd in loc_clean:
                            score = 0.8
                        elif len(dd) >= 4 and loc_clean in dd:
                            score = 0.7
                        else:
                            score = 0
                    else:
                        score = 0
                    
                    if score > best_score:
                        best_score = score
                        best_dm = dm
                
                if best_dm and best_score >= 0.7:
                    await db.execute(
                        text("UPDATE positions SET parent_position_id = :dm WHERE id = :oe"),
                        {"dm": best_dm.id, "oe": oe.id}
                    )
                    print(f"  {oe.code} -> DM ID={best_dm.id} ({best_dm.code}) fuzzy={best_score:.2f}")
                    fix2 += 1
                else:
                    # 3. Try to match OE location prefix with DM's first 4 chars
                    for dm in all_dms:
                        dd = extract_district(dm.code).upper()
                        if loc_clean and dd and len(loc_clean) >= 4 and len(dd) >= 4:
                            if loc_clean[:4] == dd[:4]:
                                await db.execute(
                                    text("UPDATE positions SET parent_position_id = :dm WHERE id = :oe"),
                                    {"dm": dm.id, "oe": oe.id}
                                )
                                print(f"  {oe.code} -> DM ID={dm.id} ({dm.code}) prefix={loc_clean[:4]}")
                                fix2 += 1
                                found = True
                                break
        
        print(f"\nFixed {fix2} OE->DM links")
        await db.flush()
        
        print("\n" + "=" * 60)
        print("STEP 3: FIX PLACEHOLDER RM -> SPH LINKS")
        print("=" * 60)
        
        for old_rm_id, new_rm_id in RM_PLACEHOLDER_TO_ACTUAL.items():
            # Check if placeholder RM exists
            q = text("SELECT id, parent_position_id FROM positions WHERE id = :rid")
            rm = (await db.execute(q, {"rid": old_rm_id})).one_or_none()
            if rm and rm.parent_position_id is None:
                await db.execute(
                    text("UPDATE positions SET parent_position_id = :sph WHERE id = :rid"),
                    {"sph": SPH_ID, "rid": old_rm_id}
                )
                print(f"  Placeholder RM ID={old_rm_id} -> SPH ID={SPH_ID}")
        
        await db.flush()
        
        # === VERIFICATION ===
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)
        
        verifications = [
            ("LT/SK with parent (any)", "SELECT COUNT(*) FROM positions WHERE role_name IN ('LAB TECHNICIAN','STOREKEEPER') AND parent_position_id IS NOT NULL", 792+859),
            ("LT/SK -> OE", "SELECT COUNT(*) FROM positions p JOIN positions parent ON parent.id = p.parent_position_id WHERE p.role_name IN ('LAB TECHNICIAN','STOREKEEPER') AND parent.role_name = 'OE'", None),
            ("OE -> DM", "SELECT COUNT(*) FROM positions p JOIN positions dm ON dm.id = p.parent_position_id WHERE p.role_name = 'OE' AND dm.role_name = 'DISTRICT MANAGER'", 182),
            ("DM -> RM (employee assigned)", """
                SELECT COUNT(*) FROM positions dm 
                JOIN positions rm ON rm.id = dm.parent_position_id 
                WHERE dm.role_name = 'DISTRICT MANAGER' 
                  AND rm.role_name LIKE '%REGIONAL%'
                  AND rm.employee_id IS NOT NULL
            """, 57),
            ("RM -> SPH/COO", """
                SELECT COUNT(*) FROM positions rm 
                JOIN positions sph ON sph.id = rm.parent_position_id 
                WHERE rm.role_name LIKE '%REGIONAL%'
            """, 10),
        ]
        
        for label, sql, expected in verifications:
            cnt = (await db.execute(text(sql))).scalar()
            expected_str = f"/{expected}" if expected else ""
            print(f"  {label}: {cnt}{expected_str}")
        
        await db.commit()
        print("\nFix committed successfully!")


if __name__ == "__main__":
    asyncio.run(fix())
