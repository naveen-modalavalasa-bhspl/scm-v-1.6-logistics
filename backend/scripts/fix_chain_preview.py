"""Apply chain preview fetch trigger fixes to LogisticsDispatch.jsx."""
import re

JSX_PATH = r"C:\Users\User-4\Downloads\bhspl_release v1.1proc\frontend\src\pages\logistics\LogisticsDispatch.jsx"

with open(JSX_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# 1. Add useEffect for re-fetching chain preview when dispatchMode changes
old1 = """  }, [selectedIssue, materialIssues]);


  const handleIndentSelect"""

new1 = """  }, [selectedIssue, materialIssues]);

  // Re-fetch chain preview when dispatch mode switches to multi-level with an already-selected MI
  useEffect(() => {
    if (dispatchMode === 'multi-level' && selectedIssue?.id) {
      fetchChainPreview(selectedIssue.id);
    } else if (dispatchMode === 'direct') {
      setChainPreview(null);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatchMode, selectedIssue?.id]);


  const handleIndentSelect"""

if old1 in content:
    content = content.replace(old1, new1, 1)
    changes += 1
    print("1. useEffect for chain re-fetch added")
else:
    print("1. SKIP - useEffect anchor not found")

# 2. Add fetchChainPreview call in handleIssueSelect after finally block
old2 = """    } finally {
      setLoadingIssue(false);
    }
  };

  const fetchChainPreview"""

new2 = """    } finally {
      setLoadingIssue(false);
    }

    // Fetch chain preview when MI is selected and mode is multi-level
    if (issueId && form.getFieldValue('dispatch_mode') === 'multi-level') {
      fetchChainPreview(issueId);
    }
  };

  const fetchChainPreview"""

if old2 in content:
    content = content.replace(old2, new2, 1)
    changes += 1
    print("2. fetchChainPreview trigger in handleIssueSelect added")
else:
    print("2. SKIP - handleIssueSelect finally anchor not found")

# 3. Add setChainPreview(null) when MI is cleared
old3 = """      setSelectedIssueItems([]);
      setSelectedIssue(null);
      setSelectedIndent(null);
      setSelectedIndentItems([]);
      form.setFieldsValue({"""

new3 = """      setSelectedIssueItems([]);
      setSelectedIssue(null);
      setSelectedIndent(null);
      setSelectedIndentItems([]);
      setChainPreview(null);
      form.setFieldsValue({"""

if old3 in content:
    content = content.replace(old3, new3, 1)
    changes += 1
    print("3. setChainPreview(null) on issue clear added")
else:
    print("3. SKIP - clear anchor not found")

# 4. Add loading spinner before chain preview card
old4 = """          {/* Chain Preview Card - shown for multi-level mode */}
          {dispatchMode === 'multi-level' && chainPreview && chainPreview.chain && chainPreview.chain.length > 0 && ("""

new4 = """          {/* Chain Preview Card - shown for multi-level mode */}
          {loadingChain && dispatchMode === 'multi-level' && (
            <div style={{ marginBottom: '20px', padding: '12px 16px', background: '#fefce8', borderRadius: '8px', border: '1px solid #fde68a', textAlign: 'center' }}>
              <Spin size="small" /> <span style={{ marginLeft: '8px', color: '#92400e', fontSize: '13px' }}>Loading custody chain preview...</span>
            </div>
          )}
          {dispatchMode === 'multi-level' && !loadingChain && chainPreview && chainPreview.chain && chainPreview.chain.length > 0 && ("""

if old4 in content:
    content = content.replace(old4, new4, 1)
    changes += 1
    print("4. Loading spinner for chain preview added")
else:
    print("4. SKIP - chain preview card anchor not found")

if changes > 0:
    with open(JSX_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✓ {changes} change(s) applied successfully.")
else:
    print("\n✗ No changes applied.")
