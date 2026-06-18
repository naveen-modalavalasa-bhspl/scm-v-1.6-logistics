"""Remove redundant fetchChainPreview call from handleIssueSelect to prevent double-fetch."""
import re

JSX_PATH = r"C:\Users\User-4\Downloads\bhspl_release v1.1proc\frontend\src\pages\logistics\LogisticsDispatch.jsx"

with open(JSX_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

old = """    } finally {
      setLoadingIssue(false);
    }

    // Fetch chain preview when MI is selected and mode is multi-level
    if (issueId && form.getFieldValue('dispatch_mode') === 'multi-level') {
      fetchChainPreview(issueId);
    }
  };

  const fetchChainPreview"""

new = """    } finally {
      setLoadingIssue(false);
    }
  };

  const fetchChainPreview"""

if old in content:
    content = content.replace(old, new, 1)
    with open(JSX_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Redundant fetchChainPreview call removed from handleIssueSelect")
else:
    print("✗ Anchor not found - checking alternatives")
    # Check if it was already removed
    if "} finally {\n      setLoadingIssue(false);\n    }\n  };\n\n  const fetchChainPreview" in content:
        print("  Already clean - no double-fetch call present")
    else:
        print("  Pattern not found, file may have different formatting")
