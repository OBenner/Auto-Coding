# Performance Testing Guide - Virtual Scrolling for Task Logs

This guide documents the manual performance testing procedure for the virtual scrolling implementation in TaskDetailModal.

## Test Objectives

Validate that virtual scrolling provides significant performance improvements when rendering large log files (1000+ entries).

### Target Metrics

- **Initial render time**: <100ms (down from >500ms)
- **Scrolling performance**: Smooth 60fps
- **Memory usage**: Reduced (only visible items rendered)
- **UI responsiveness**: Instant phase/entry expand/collapse

## Prerequisites

1. **Generate test data**:
   ```bash
   cd apps/frontend
   npx tsx scripts/generate-test-logs.ts 1000 test-logs-1000.json
   npx tsx scripts/generate-test-logs.ts 2000 test-logs-2000.json
   npx tsx scripts/generate-test-logs.ts 5000 test-logs-5000.json
   ```

2. **Start the application**:
   ```bash
   npm run dev
   ```

3. **Open DevTools**:
   - Press F12 or Cmd+Option+I (Mac) / Ctrl+Shift+I (Windows)
   - Navigate to the **Performance** tab

## Test Procedure

### Test 1: Initial Render Performance

**Goal**: Measure time from opening logs tab to first paint

1. Open a task with test logs (1000+ entries)
2. In DevTools Performance tab, click **Record** (●)
3. Click on the **Logs** tab in TaskDetailModal
4. Stop recording after logs appear
5. Analyze the flame chart:
   - Look for **TaskLogs** component render time
   - Measure from click to paint
   - **Target**: <100ms total

**Expected Result**: Initial render completes in <100ms

---

### Test 2: Scrolling Performance

**Goal**: Verify smooth 60fps scrolling through large log lists

1. Open logs tab with 1000+ entries
2. Start Performance recording
3. Scroll continuously through the entire log list (top to bottom)
4. Stop recording
5. In the **Summary** tab, check:
   - **FPS**: Should be consistently near 60fps
   - **Scripting time**: Should be minimal during scroll
   - **Rendering time**: Should be consistent

**Expected Result**: Smooth scrolling at ~60fps with no frame drops

---

### Test 3: Memory Usage Comparison

**Goal**: Confirm reduced memory footprint

1. Open DevTools **Memory** tab
2. Click **Take heap snapshot** (Baseline)
3. Open logs tab with 5000 entries
4. Expand all phases
5. Click **Take heap snapshot** (After render)
6. Compare snapshots:
   - Look for TaskLogs-related objects
   - Count rendered DOM nodes (should be ~50-100, not 5000)
   - Check total heap size increase

**Expected Result**: Only ~50-100 log entries rendered in DOM (not all 5000)

---

### Test 4: Phase Expansion Performance

**Goal**: Verify instant phase expand/collapse

1. Open logs tab with 1000+ entries in coding phase
2. Start Performance recording
3. Click to collapse the coding phase (hiding 600+ entries)
4. Click to expand it again
5. Stop recording
6. Measure interaction time

**Expected Result**: Expand/collapse completes in <50ms

---

### Test 5: Entry Detail Expansion

**Goal**: Verify instant log entry detail expand/collapse

1. Open logs tab with test data
2. Expand a phase with many entries
3. Start Performance recording
4. Click to expand a log entry's detail section
5. Click to collapse it
6. Stop recording
7. Measure interaction time

**Expected Result**: Detail expand/collapse is instant (<20ms)

---

### Test 6: Visual Integrity

**Goal**: Ensure no visual glitches or missing content

1. Open logs tab with 2000+ entries
2. Rapidly scroll up and down
3. Check for:
   - ✅ No blank spaces between entries
   - ✅ No overlapping entries
   - ✅ Proper phase headers at correct positions
   - ✅ Correct entry content and styling
   - ✅ Detail sections render when expanded
   - ✅ No content "popping in" after scroll stops

**Expected Result**: All entries render correctly without glitches

---

### Test 7: Stress Test (5000+ entries)

**Goal**: Validate performance with extreme data volumes

1. Generate 5000+ entry test logs
2. Open logs tab
3. Measure:
   - Initial render time
   - Scroll performance
   - Memory usage
   - Responsiveness

**Expected Result**: Still maintains <100ms render, smooth scrolling

---

## Baseline Comparison (Optional)

To compare with non-virtualized performance:

1. **Checkout main branch**:
   ```bash
   git checkout main
   ```

2. Run the same tests
3. Document the differences:
   - Initial render time (likely >500ms for 1000+ entries)
   - Memory usage (all entries in DOM)
   - Scrolling FPS (likely lower, especially on slower machines)

4. **Return to feature branch**:
   ```bash
   git checkout auto-claude/010-implement-virtual-scrolling-for-large-task-logs-in
   ```

## Recording Results

Document your findings:

```markdown
### Performance Test Results

**Test Environment**:
- OS: [macOS / Windows / Linux]
- Browser: [Chrome 120.x / Edge 120.x]
- CPU: [Processor model]
- RAM: [Amount]

**Test 1: Initial Render (1000 entries)**
- Time: [X]ms
- Target: <100ms
- Status: [✅ Pass / ❌ Fail]

**Test 2: Scrolling (1000 entries)**
- Average FPS: [X]
- Target: ~60fps
- Status: [✅ Pass / ❌ Fail]

**Test 3: Memory Usage (5000 entries)**
- DOM nodes rendered: [X]
- Target: <150 nodes (not all 5000)
- Status: [✅ Pass / ❌ Fail]

**Test 4: Phase Expansion**
- Time: [X]ms
- Target: <50ms
- Status: [✅ Pass / ❌ Fail]

**Test 5: Entry Detail Expansion**
- Time: [X]ms
- Target: <20ms
- Status: [✅ Pass / ❌ Fail]

**Test 6: Visual Integrity**
- Glitches observed: [Yes/No - describe if any]
- Status: [✅ Pass / ❌ Fail]

**Test 7: Stress Test (5000 entries)**
- Initial render: [X]ms
- Scrolling FPS: [X]
- Status: [✅ Pass / ❌ Fail]

**Overall Assessment**: [Pass / Fail]
**Notes**: [Any additional observations]
```

## Troubleshooting

### Issue: Logs don't appear

**Solution**: Ensure test logs file is correctly formatted JSON and placed in the correct task directory.

### Issue: Performance is worse than expected

**Check**:
1. DevTools is open (adds overhead - this is expected)
2. Other browser tabs/extensions consuming resources
3. Test data is correctly structured (phases.planning/coding/validation)

### Issue: Visual glitches during scroll

**Check**:
1. Estimated heights in `useVirtualizedLogs.ts` match actual rendered heights
2. `overscan` value (currently 5) may need adjustment
3. Browser zoom level (should be 100%)

## Next Steps

After completing all tests:

1. ✅ Document results in this guide
2. ✅ Update `build-progress.txt` with findings
3. ✅ Mark subtask-3-1 as completed in `implementation_plan.json`
4. ✅ Commit changes with results summary

## Additional Resources

- [React Virtual Documentation](https://tanstack.com/virtual/latest)
- [Chrome DevTools Performance](https://developer.chrome.com/docs/devtools/performance/)
- [Measuring Web Performance](https://web.dev/user-centric-performance-metrics/)
