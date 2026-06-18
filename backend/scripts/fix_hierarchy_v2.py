"""
Fix hierarchy links - V2 with corrected OE location extraction.

Bug in V1: For OE codes in format OE-AP-104-MMU-LOCATION, the extraction
was removing "OE-" prefix but the remaining "AP-104-MMU-LOCATION" wasn't
being parsed to find the location at the end.

Fix: Extract location as the LAST dash-separated segment for dash-format OEs.
Also: Use more precise DM matching - match location name to the FULL district name.
"""
import asyncio
import sys
sys.path.insert(0, '.')
from app.database import AsyncSessionLocal
from sqlalchemy import text


# RM placeholder -> actual RM with employee
RM_PLACEHOLDER_TO_ACTUAL = {
    5900: 3,    # REGIONAL-AP-104-MMU-MANAGER-VIJAYAWADA -> RM@VIJAYWADA (Himaja Sai Vaani Ganta)
    5928: 136,  # REGIONAL-MANAGER-AP-104-MMU-ONGOLE -> REGIONAL MANAGER@ONGOLE (Kaleem Mohammed)
    5901: 137,  # REGIONAL-MANAGER-AP-104-MMU-VIZIANAGARAM -> RM@VIZIANAGARAM (Laxman Rao Allam)
    5922: 138,  # REGIONAL-MANAGER-AP-104-MMU-YSR-KADAPA -> REGIONAL MANAGER@YSR KADAPA (Shaik Ikbal Hussain)
}

SPH_ID = 5929


def extract_oe_location(code: str) -> str:
    """Extract location name from OE position code."""
    c = code.upper()
    
    # Remove common suffixes
    for s in ["-AP-104-MMUS", "-AP-104-MMU"]:
        c = c.replace(s, "")
    
    if "@" in c:
        # Format: OE@LOCATION or OELOCATION@
        if c.startswith("OE@"):
            loc = c.split("@")[1]
        else:
            loc = c.split("@")[0].replace("OE", "")
    else:
        # Format: OE-AP-104-MMU-LOCATION or OE-MMU-NNN
        # Remove OE- prefix
        c = c.replace("OE-", "")
        # For "AP-104-MMU-LOCATION", split by dash and take last part
        parts = [p for p in c.split("-") if p]
        if parts:
            # Check if it's a numbered MMU (like MMU-020)
            if parts[0] == "MMU" and len(parts) > 1 and parts[1].isdigit():
                return ""  # Generic MMU position, no specific location
            loc = parts[-1]  # Last part is the location
        else:
            loc = ""
    
    return loc.strip()


def extract_district(code: str) -> str:
    """Extract district name from DM position code."""
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
            if parts[0] == "DM" and parts[1] == "0001":
                return "NTR"
            d = parts[-1]
        else:
            d = c
    
    d = d.strip(" -_")
    if d.startswith("DISTRICTMANAGER"):
        d = d.replace("DISTRICTMANAGER", "")
    return d


# Map district names (both short-code and full-name) to RM IDs
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

# Manual OE location -> correct DM ID mapping
# These are specific town/village locations that can't be auto-matched to districts
# Format: location_upper -> DM position id
LOCATION_TO_DM = {
    # VIZIANAGARAM region DM (ID=5819)
    "VIZIANAGARAM": 5819, "BOBBILI": 5819, "RAJAM": 5819, "SRUNGAVARAPUKOTA": 5819,
    "CHEEPURUPALLI": 5819, "GARIVIDI": 5819, "NELLIMARLA": 5819,
    "DENKADA": 5819, "MERAKAMUDIDAM": 5819, "RAMABHADRAPURAM": 5819,
    "KOTABOMMALI": 5819, "PALASA": 5819, "TEKKALI": 5819,
    "NARSANNAPETA": 5819, "PATHAPATNAM": 5819, "SOMPETA": 5819,
    "SANTHABOMMALI": 5819, "KOTTURU": 5819, "BALIJIPETA": 5819,
    "SALURU": 5819, "PARVATHIPURAM": 5819, "KURUPAM": 5819, "SEETHANAGARAM": 5819,
    "GARUGUBILLI": 5819, "BHOGAPURAM": 5819, "GANTYADA": 5819, "JAMI": 5819,
    "SRIKAKULAM": 5819, "NARASANNAPETA": 5819, "PALAKONDA": 5819,
    "VAJRAPUKOTHURU": 5819, "SARAVAKOTA": 5819, "DORAVARISATRAM": 5819,
    "BALAYAPALLI": 5819, "CHITTAMUR": 5819, "JALUMURU": 5819,
    "PONDURU": 5819, "KURUGUMBA": 5819, "KOMARADA": 5819, "PACHIPENTA": 5819,
    "GUMMALAXMIPURAM": 5819,
    
    # PRAKASAM region DM (ID=5848)
    "PRAKASAM": 5848, "ADDANKI": 5848, "ONGOLE": 5848, "KANDUKURU": 5848,
    "KANDUKUR": 5848, "MARKAPURAM": 5848, "MARKAPUR": 5848,
    "KANIGIRI": 5848, "PAMUR": 5848, "PODILI": 5848, "DORNALA": 5848,
    "GIDDALUR": 5848, "YERRAGONDAPALEM": 5848, "KOMAROLE": 5848,
    "CHIMAKURTHI": 5848, "MARTUR": 5848, "PARCHUR": 5848,
    "SANTHANUTHALAPADU": 5848, "BESTAVARIPETA": 5848,
    "HANUMANTHUNIPADU": 5848, "PAMULAPADU": 5848, "PULLALACHERUVU": 5848,
    "VELIGANDLA": 5848, "SATTENAPALLI": 5848, "GURAZALA": 5848,
    "NARASARAOPET": 5848, "NARASARAOPET-DIVISION": 5848,
    "VINUKONDA": 5848, "PIDUGURALLA": 5848, "MACHAVARAM": 5848,
    "CHILAKALURIPETA": 5848, "SATULURU": 5848,
    
    # KAKINADA region DM (ID=5857)
    "KAKINADA": 5857, "PEDDAPURAM": 5857, "PEDDAPURAM": 5857, "PITHAPURAM": 5857,
    "SAMALKOT": 5857, "TUNI": 5857, "KOTHAPETA": 5857, "ALAMURU": 5857,
    "ANAPARTHI": 5857,
    
    # EAST GODAVARI region DM (ID=5862)
    "EAST": 5862, "GODAVARI": 5862, "KOVVUR": 5862, "ANANPARTHI": 5862,
    "RAJAHMUNDRY": 5862, "RAJAMUNDRY": 5862, "MANDAPETA": 5862,
    "RAMACHANDRAPURAM": 5862, "RAMPACHODAVARAM": 5862, "YELESWARAM": 5862,
    "RAJAVOMMANGI": 5862, "KORUKONDA": 5862, "THALLAREVU": 5862,
    "KOTHALANKA": 5862, "KAPILESWARAPURAM": 5862,
    
    # KONASEEMA region DM (ID=5867)
    "KONASEEMA": 5867, "AMALAPURAM": 5867,  "RAZOLE": 5867,
    "MUMIDIVARAM": 5867, "KATRENIKONA": 5867, "MALLAVALLI": 5867,
    "PEDAPUDI": 5867, "MUMMIDIVARAM": 5867,
    
    # ANANTHAPUR region DM (many locations)
    "ANANTAPUR": 5921, "ANANTHAPUR": 5921, "KALYANDURG": 5921,
    "DHARMAVARAM": 5921, "DHARMAVARAM": 5921, "GUNTAKAL": 5921,
    "TADIPATRI": 5921, "TADIPATHRI": 5921, "GORANTLA": 5921,
    "KUDERU": 5921, "PENUGONDA": 5921, "PEDDAPAPPUR": 5921,
    "BOMMAGATTA": 5921, "CHENNEKOTHAPALLI": 5921,
    "RAYADURG": 5921, "URAVAKONDA": 5921, "MADAKASIRA": 5921,
    "HINDUPUR": 5921, "KADIRI": 5921, "KADIRI": 5921,
    
    # YSR KADAPA region DM (ID=5907)
    "KADAPA": 5907, "YSR": 5907, "PRODDATUR": 5907, "PRODDATUR": 5907,
    "BADVEL": 5907, "JAMMALAMADUGU": 5907, "KAMALAPURAM": 5907,
    "PULIVENDULA": 5907, "RAJAMPETA": 5907, "RAYACHOTI": 5907,
    "RAILCODE": 5907, "MYDUKUR": 5907, "PENDLIMARRI": 5907,
    
    # GUNTUR region DM (ID=5927)
    "GUNTUR": 5927, "GURAZALA": 5927, "MACHAVARAM": 5927, "SATTENAPALLI": 5927,
    "MANGALAGIRI": 5927, "TENALI": 5927, "NARASARAOPET": 5927,
    "PONNUR": 5927, "VINUKONDA": 5927, "PIDUGURALLA": 5927,
    "KAREMPUDI": 5927, "REPALLE": 5927, "BAPATLA": 5925, "BAPATLA-DIVISION": 5925,
    "BAPATLA-TWO": 5925, "CHIRALA": 5925, "CHIRALA-DIVISION": 5925,
    "VETAPALEM": 5925, "PALNADU": 5926, "JAGGAYYAPETA": 5930,
    
    # KRISHNA region DM (ID=5923)
    "KRISHNA": 5923, "NUZVID": 5923, "GUDIVADA": 5923, "MACHILIPATNAM": 5923,
    "KANKIPADU": 5923, "TIRUVURU": 5923, "BANTUMILLI": 5923,
    "KALIDINDI": 5923, "MOVVA": 5923, "PENUGUDURU": 5923,
    
    # NTR region DM (ID=5930)
    "NTR": 5930, "JAGGAYAPETA": 5930, "JAGGAYAPETADIVISION": 5930,
    
    # KURNOOL region DM (ID=5916)
    "KURNOOL": 5916, "ADONI": 5916, "NANDYAL": 5908, "NANDYAL": 5908,
    "DHONE": 5916, "DHONE-TWO": 5916, "ATMAKUR": 5908, "ATMAKUR-ONE": 5908,
    "BANAGANAPALLE": 5908, "SIRVEL": 5908, "ALLAGADDA": 5908,
    "KOILKUNTLA": 5908, "PANYAM": 5908, "GADIVEMULA": 5908,
    "ACHAMPETA": 5908, "NANDIKOTKUR": 5908,
    
    # CHITTOOR region DM (ID=5918)
    "CHITTO0R": 5918, "CHITTOOR": 5918, "TIRUPATHI": 5902, "TIRUPATI": 5902,
    "NAGARI": 5902, "SRINIVASAPURAM": 5902, "PUTTUR": 5902,
    "SRIKALHASTI": 5902, "PALAMANER": 5902, "SRIKALAHASTI": 5902,
    "KUPPAM": 5918, "PALAMANER": 5918, "MADANAPALLE": 5918,
    "PUNGANUR": 5918, "SODAM": 5918, "BANGARUPALEM": 5918,
    "SANTHIPURAM": 5918, "PALASAMUDRAM": 5918,
    "SRI SATYA SAI": 5912, "SRI-SATYA-SAI": 5912, "DHARMAVARAM": 5912,
    
    # NELLORE region DM (ID=5909)
    "SPSR": 5909, "NELLORE": 5909, "KAVALI": 5909, "GUDUR": 5909,
    "NAIDUPETA": 5909, "VENKATAGIRI": 5909, "VARIKUNTAPADU": 5909,
    "DUTTALUR": 5909, "BUCHIREDDIPALEM": 5909, "INDUKURUPETA": 5909,
    "VENGALAM": 5909, "KONDAPURAM": 5909, "KOTA": 5909,
    "ANUMASAMUDRAMPETA": 5909, "JALADANKI": 5909, "RAPUR": 5909,
    "PODALAKUR": 5909, "SULLURUPETA": 5909, "SULURPETA": 5909,
    "CHENNAKESAMPALLI": 5909, "PENGALUR": 5909,
    
    # ELURU region DM (ID=5917)
    "ELURU": 5917, "BHIMAVARAM": 5917, "NARSAPURAM": 5917,
    "PALAKOL": 5917, "NIDADAVOLE": 5917, "UNKURU": 5917,
    "AKIVEEDU": 5917, "KOVVUR": 5917, "CHINTALAPUDI": 5917,
    "GANAPAVARAM": 5917, "TADEPALLIGUDEM": 5917, "JANGAREDDIGUDEM": 5917,
    "NALLAGARUVU": 5917, "DHULIPUDI": 5917, "DENDULURU": 5917,
    
    # VISAKHAPATNAM region (ID=5899)
    "VISAKAPATNAM": 5899, "VISAKHAPATNAM": 437, "ANAKAPALLI": 5880,
    "NARSIPATNAM": 5880, "PADERU": 5880, "CHITTAMUR": 5880,
    "ITDA": 5880, "ITDA-ARAKUVALLEY": 5880, "ARAKUVALLEY": 5880,
    "ARAKU": 5880, "NAKKAPALLI": 5880, "YELAMANCHILI": 5880,
    "PAYAKARAOPETA": 5880, "MADUGULA": 5880, "GMADUGULA": 5880,
    "CHODAVARAM": 5880, "KOTHAVALASA": 5880, "ANANDAPURAM": 5880,
    "BHEEMILI": 5880, "GAJAPATHINAGARAM": 5880,
    
    # WEST GODAVARI region DM (ID=5910)
    "WEST": 5910, "GODAVARI": 5910,
    
    # SRIKAKULAM region DM (ID=5911)
    "SRIKAKULAM": 5911,
    
    # PARVATHIPURAM region DM (ID=5914)
    "PARVATHIPURAM": 5914,
    
    # MARKAPURAM region DM (ID=5915)
    "MARKAPURAM": 5915,
    
    # POLAVARAM DM (ID=5913)
    "POLAVARAM": 5913,
    
    # ASR DM (ID=5919)
    "ASR": 5919,
    
    # ANNAMAYYA DM (ID=5920)
    "ANNAMAYYA": 5920,
    
    # NTR DM(5930) generic
    "NTR": 5930,
}

# OE-MMU-NNN type positions -> default to NTR DM
MMU_OE_DM = 5930


async def fix_v2():
    async with AsyncSessionLocal() as db:
        # === STEP 0: Revert bad OE links from V1 ===
        print("=" * 60)
        print("STEP 0: Revert V1 incorrect OE links")
        print("=" * 60)
        # Reset ALL OEs that previously had NULL parent_position_id
        # The 96 linked OEs had parent_position_id BEFORE we ran V1
        # We know the IDs of the original 96 linked OEs by filtering on @ format
        # All V1 changes were to OEs that had NULL parent. Reset them all.
        
        q = text("SELECT COUNT(*) FROM positions WHERE role_name = 'OE' AND parent_position_id IS NOT NULL")
        before = (await db.execute(q)).scalar()
        print(f"OEs WITH parent before revert: {before}")
        
        # Reset OEs that were linked in V1 but had location mismatch
        # Strategy: reset ALL OEs, then re-apply only the correct 96 from @ format
        await db.execute(text("UPDATE positions SET parent_position_id = NULL WHERE role_name = 'OE' AND code NOT LIKE '%@%' AND code NOT LIKE 'OE-MMU-%'"))
        
        await db.flush()
        
        after_reset = (await db.execute(text("SELECT COUNT(*) FROM positions WHERE role_name = 'OE' AND parent_position_id IS NOT NULL"))).scalar()
        print(f"OEs WITH parent after resetting dash-format: {after_reset}")
        
        # === STEP 1: Restore DM -> RM links ===
        print("\n" + "=" * 60)
        print("STEP 1: Update DM -> RM links to point to correct RM with employee")
        print("=" * 60)
        
        q = text("SELECT id, code FROM positions WHERE role_name = 'DISTRICT MANAGER'")
        dms = (await db.execute(q)).all()
        
        fix1 = 0
        for dm in dms:
            district = extract_district(dm.code)
            target_rm = None
            # Match district name to RM
            for dname, rm_id in DISTRICT_TO_RM.items():
                if district.upper() in dname.upper() or dname.upper() in district.upper():
                    target_rm = rm_id
                    break
            
            if target_rm:
                await db.execute(
                    text("UPDATE positions SET parent_position_id = :rm WHERE id = :dm"),
                    {"rm": target_rm, "dm": dm.id}
                )
                fix1 += 1
        
        print(f"Updated {fix1} DM -> RM links")
        await db.flush()
        
        # === STEP 2: Assign OEs to correct DMs using manual mapping ===
        print("\n" + "=" * 60)
        print("STEP 2: Assign OE positions to correct DMs")
        print("=" * 60)
        
        # First, get OEs that already have parents (the @-format ones) and re-verify them
        q = text("SELECT id, code, parent_position_id FROM positions WHERE role_name = 'OE'")
        all_oes = (await db.execute(q)).all()
        
        already_linked = [o for o in all_oes if o.parent_position_id is not None]
        unlinked = [o for o in all_oes if o.parent_position_id is None]
        
        print(f"Already linked OEs: {len(already_linked)}")
        print(f"Unlinked OEs: {len(unlinked)}")
        
        # Process unlinked OEs
        fix2_count = 0
        no_match = []
        
        for oe in unlinked:
            oe_loc = extract_oe_location(oe.code)
            if not oe_loc:
                # Generic OE with no location - assign to NTR DM
                await db.execute(
                    text("UPDATE positions SET parent_position_id = :dm WHERE id = :oe"),
                    {"dm": MMU_OE_DM, "oe": oe.id}
                )
                print(f"  {oe.code}: Generic OE -> DM ID={MMU_OE_DM} (NTR)")
                fix2_count += 1
                continue
            
            # Try exact match
            dm_id = None
            if oe_loc in LOCATION_TO_DM:
                dm_id = LOCATION_TO_DM[oe_loc]
            else:
                # Try partial match - check if OE location is a substring of any key
                for loc_key, did in LOCATION_TO_DM.items():
                    if oe_loc in loc_key or loc_key in oe_loc:
                        dm_id = did
                        break
            
            if dm_id:
                await db.execute(
                    text("UPDATE positions SET parent_position_id = :dm WHERE id = :oe"),
                    {"dm": dm_id, "oe": oe.id}
                )
                print(f"  {oe.code} (loc={oe_loc}) -> DM ID={dm_id}")
                fix2_count += 1
            else:
                no_match.append((oe.id, oe.code, oe_loc))
        
        if no_match:
            print(f"\n  UNMATCHED OEs ({len(no_match)}):")
            for oid, code, loc in no_match:
                print(f"    ID={oid}: {code} (loc='{loc}')")
        
        print(f"\nAssigned {fix2_count} OEs to DMs")
        
        await db.flush()
        
        # === STEP 3: Fix placeholder RM -> SPH links ===
        print("\n" + "=" * 60)
        print("STEP 3: Fix placeholder RM -> SPH links")
        print("=" * 60)
        
        for old_rm_id, new_rm_id in RM_PLACEHOLDER_TO_ACTUAL.items():
            q = text("SELECT parent_position_id FROM positions WHERE id = :rid")
            rm = (await db.execute(q, {"rid": old_rm_id})).one_or_none()
            if rm and rm.parent_position_id is None:
                await db.execute(
                    text("UPDATE positions SET parent_position_id = :sph WHERE id = :rid"),
                    {"sph": SPH_ID, "rid": old_rm_id}
                )
                print(f"  Placeholder RM ID={old_rm_id} -> SPH ID={SPH_ID}")
            elif rm:
                print(f"  Placeholder RM ID={old_rm_id} already has parent={rm.parent_position_id}")
        
        await db.flush()
        
        # === VERIFICATION ===
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)
        
        checks = [
            ("LT/SK -> OE", 
             "SELECT COUNT(*) FROM positions p JOIN positions oe ON oe.id = p.parent_position_id WHERE p.role_name IN ('LAB TECHNICIAN','STOREKEEPER') AND oe.role_name = 'OE'"),
            ("OE -> DM", 
             "SELECT COUNT(*) FROM positions p JOIN positions dm ON dm.id = p.parent_position_id WHERE p.role_name = 'OE' AND dm.role_name = 'DISTRICT MANAGER'"),
            ("DM -> RM (with employee)", 
             "SELECT COUNT(*) FROM positions dm JOIN positions rm ON rm.id = dm.parent_position_id WHERE dm.role_name = 'DISTRICT MANAGER' AND rm.employee_id IS NOT NULL"),
            ("RM -> SPH", 
             "SELECT COUNT(*) FROM positions rm JOIN positions sph ON sph.id = rm.parent_position_id WHERE rm.role_name LIKE '%REGIONAL%'"),
        ]
        
        totals = {
            "LT/SK -> OE": 1651,
            "OE -> DM": 182,
            "DM -> RM (with employee)": 57,
            "RM -> SPH": 10,
        }
        
        for label, sql in checks:
            cnt = (await db.execute(text(sql))).scalar()
            total = totals.get(label, "?")
            print(f"  {label}: {cnt}/{total}")
        
        await db.commit()
        print("\nV2 fix committed successfully!")


if __name__ == "__main__":
    asyncio.run(fix_v2())
