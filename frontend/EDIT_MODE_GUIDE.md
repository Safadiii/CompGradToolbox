# Edit & Override Mode Guide

## Overview

The Edit Mode allows you to manually adjust TA assignments after the algorithm runs, giving you complete control over the final assignments.

## Accessing Edit Mode

1. After viewing results, click the **"✏️ Edit Assignments"** button
2. You'll enter the Edit View where you can modify assignments
3. Changes are temporary until you click "Save Changes"

## Edit Operations

### Remove a TA

**What it does**: Removes a TA from a professor's assignment

**How to do it**:
1. Find the professor in the professor assignments section
2. Click the **✕** button on the TA's tag
3. TA is removed from assignments
4. Workload count updates automatically

**Example**:
```
Before: ProfA → [TA1 ✕] [TA3 ✕]
After:  ProfA → [TA3 ✕]
```

### Add a TA

**What it does**: Adds an unassigned TA to a professor's assignment

**How to do it**:
1. Scroll to the professor's section
2. Look for the "Add TA:" section with available TAs
3. Click **"+ TA Name"** button next to the TA you want
4. TA is added to the professor
5. Workload updates automatically

**Example**:
```
Before: ProfA → [TA1] [TA3]
        Unassigned: + TA2, + TA5

After:  ProfA → [TA1] [TA3] [TA2]
        Unassigned: + TA5
```

## Real-time Updates

As you make changes:
- ✅ **TA Workload Summary** updates instantly
- ✅ **Assignments count** recalculates
- ✅ **Available TAs** list changes
- ✅ **No errors or conflicts** - system prevents duplicates

## Important Notes

### Cannot Add:
- ✗ TA already assigned to that professor
- ✗ TA who would duplicate (auto-prevented)

### Each Change:
- Updates workload counts
- Removes from available pool when assigned
- Adds back to available when removed

## Workflow Example

**Scenario**: You want to swap TA2 and TA5 between professors

### Step 1: View Results
```
ProfA → [TA1, TA2]
ProfB → [TA4, TA5]
```

### Step 2: Click "Edit Assignments"
- Enters Edit Mode

### Step 3: Make Changes
- Remove TA2 from ProfA (click ✕)
- Add TA5 to ProfA (click "+ TA5")
- Remove TA5 from ProfB (click ✕)
- Add TA2 to ProfB (click "+ TA2")

### Step 4: View Changes
```
ProfA → [TA1, TA5]
ProfB → [TA4, TA2]
```

### Step 5: Save
- Click "✓ Save Changes"
- Changes are locked in
- Results view shows updated assignments

## Workload Distribution

The system automatically tracks workload:

**Workload Summary shows**:
- Each TA's assignment count
- Real-time updates as you edit
- Visual representation on results

**Example**:
```
Before Edits:          After Edits:
TA1: 1                 TA1: 1
TA2: 1                 TA2: 2 ← increased
TA3: 1                 TA3: 1
TA4: 1                 TA4: 1
TA5: 1                 TA5: 1 ← decreased
```

## Saving & Canceling

### Save Changes
- Click **"✓ Save Changes"** button
- Returns to results view with modified data
- Assignment shows "(modified)" indicator
- All changes are preserved
- Can export modified results

### Cancel Changes
- Click **"✕ Cancel"** button
- Discards all edits
- Returns to original results
- No data is lost (original preserved)

## Tips & Best Practices

### ✅ DO:
- Edit one change at a time for clarity
- Check workload summary after changes
- Save frequently if making many changes
- Export results after editing
- Use Edit mode to fine-tune algorithm results

### ❌ DON'T:
- Try to add duplicate TAs (prevented by system)
- Lose track of original assignments (keep original data)
- Make changes without understanding impact
- Export before saving edits

## Common Scenarios

### Scenario 1: Balance Workload

**Goal**: Distribute work more evenly

**Steps**:
1. Click Edit Assignments
2. Identify TA with high workload
3. Remove one assignment
4. Add that TA to professor with low workload TA
5. Click Save

### Scenario 2: Fix Preference Conflicts

**Goal**: Respect specific TA/Professor preferences not in algorithm

**Steps**:
1. Identify the conflict
2. Click Edit Assignments
3. Remove conflicting assignments
4. Add preferred pairs
5. Save changes

### Scenario 3: Handle Availability Issues

**Goal**: Adjust for TA availability discovered after algorithm

**Steps**:
1. Identify unavailable TA
2. Click Edit Assignments
3. Remove TA from professor
4. Add another available TA
5. Save changes

## Export After Editing

**To save your edits permanently**:
1. After editing and returning to results
2. Click **"📥 Export as JSON"**
3. File downloaded with timestamp
4. Contains your modified assignments

**Export file includes**:
- All professor assignments
- Updated TA workloads
- Timestamp of export

## Comparison: Before & After Edits

### Visual Indicator

When you've made edits, results view shows:
```
Assignment Results
Manual assignment (modified)  ← Shows modifications
```

### Full Data Available

You can see:
- Original results by clicking "New Assignment" and redoing
- Modified results by comparing exported files
- Changes by looking at workload differences

## UI Elements Explained

### Edit Mode Header
```
Edit Assignments
Customize the assignment by adding or removing TAs
```

### Edit Badge
```
✏️ Edit Mode: Modify Assignments
```

### Professor Cards
```
[Professor Name]
[TA1 ✕] [TA2 ✕]          ← Assigned TAs with remove buttons
Add TA:
[+ TA3] [+ TA4] [+ TA5]   ← Unassigned TAs to add
```

### Workload Summary
```
TA1  [count badge]
TA2  [count badge]
...
```

### Action Buttons
```
[✓ Save Changes]  [✕ Cancel]
```

## Keyboard Shortcuts

- **Tab**: Navigate between elements
- **Enter**: Activate buttons
- **Escape**: Cancel edits (future enhancement)

## Troubleshooting Edit Mode

### Can't find TA to add
- **Reason**: TA is already assigned elsewhere
- **Solution**: Remove TA from other professor first

### Changes not saving
- **Solution**: Click "✓ Save Changes" button explicitly
- **Info**: Canceling discards changes automatically

### Don't see workload updates
- **Solution**: Scroll down to see Workload Summary section
- **Info**: Updates happen in real-time

### Want to revert changes
- **Solution**: Click "✕ Cancel" button (before saving)
- **Info**: Saved changes can be undone by running new assignment

## Advanced Usage

### Bulk Operations

To move multiple TAs:
1. Enter Edit Mode
2. Make multiple removals
3. Add multiple TAs to new professor
4. Save when complete

### Workload Optimization

To optimize workload:
1. Check workload summary
2. Identify imbalances
3. Move TAs from overloaded to underloaded professors
4. Verify balance improves
5. Save changes

### Algorithm Override

To completely override algorithm:
1. Remove all problematic assignments
2. Manually add preferred combinations
3. Save your custom assignments
4. Export results

## Export Options

After editing, you can:

1. **Export JSON**: Download modified results
2. **Print**: Use browser print function
3. **Share**: Send exported JSON file
4. **Archive**: Save for records

## Undo Functionality (Future)

Currently: Click Cancel before saving to discard edits

Future enhancement: Undo button to revert individual changes

## Performance Notes

- Edit mode works smoothly with 50+ TAs/Professors
- Instant updates on all changes
- No lag in workload calculations
- Smooth animations throughout

---

**Need Help?** Review this guide or check system documentation.

**Ready to Edit?** Click "✏️ Edit Assignments" on the results screen!
