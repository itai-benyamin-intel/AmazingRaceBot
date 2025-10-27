# Checklist Feature

The checklist feature allows participants to submit answers progressively, one item at a time, instead of requiring all answers at once. This is particularly useful for multi-part questions and list-based challenges.

## Overview

When a challenge is configured as a checklist, participants can:
- Submit individual items from the list, one at a time
- Submit multiple items in a single submission
- See their progress with a visual checklist showing completed and pending items
- Track which items have been answered and which remain

## Configuration

To create a checklist challenge, use `checklist_items` in the verification configuration instead of `answer`:

```yaml
challenges:
  - id: 5
    name: "Capital Cities Challenge"
    description: "Name 5 capital cities from different continents"
    location: "Anywhere"
    type: "multi_choice"
    verification:
      method: "answer"
      checklist_items:
        - "Tokyo"
        - "Paris"
        - "Cairo"
        - "Brasilia"
        - "Canberra"
    hints:
      - "Think about Asia, Europe, Africa, South America, and Australia"
```

## How It Works

### For Participants

1. **View the challenge**: Use `/current` to see the full checklist with progress indicators
   ```
   📝 Checklist Items:
   ⬜ Tokyo
   ⬜ Paris
   ⬜ Cairo
   ⬜ Brasilia
   ⬜ Canberra
   
   Progress: 0/5 items completed
   ```

2. **Submit answers**: Use `/submit <answer>` to submit items one at a time
   ```
   /submit Tokyo
   ```

3. **See progress**: After each submission, the bot shows updated progress
   ```
   📝 Checklist Progress
   
   ✅ Tokyo
   ⬜ Paris
   ⬜ Cairo
   ⬜ Brasilia
   ⬜ Canberra
   
   Progress: 1/5 items completed
   ✅ Added: Tokyo
   
   Keep submitting answers to complete remaining items!
   ```

4. **Complete the challenge**: When all items are submitted, the challenge is marked as complete
   ```
   ✅ Correct! Team 'Alpha' completed:
   Capital Cities Challenge
   Progress: 5/9 challenges
   ```

### Submission Options

Participants can submit answers in several ways:

1. **Single item**: `/submit Tokyo`
2. **Multiple words**: `/submit The capital is Tokyo`
3. **Natural language**: Items are matched even when embedded in longer text
4. **Case-insensitive**: `tokyo`, `TOKYO`, and `Tokyo` all match

## Benefits

### For Participants

- **Progressive completion**: Make progress even without knowing all answers
- **Team collaboration**: Different team members can contribute different items
- **Clear visibility**: Always see which items are done and which remain
- **Flexible submission**: Submit items as you discover them, no need to wait

### For Game Organizers

- **Engaging challenges**: More interactive than all-or-nothing questions
- **Fair difficulty**: Teams aren't stuck if they can't remember one item
- **Better tracking**: See partial progress for each team
- **Versatile use cases**: Works for many types of list-based challenges

## Use Cases

Perfect for challenges like:

1. **Geography**: "Name 5 capital cities"
2. **History**: "List 3 inventors from the Industrial Revolution"
3. **Science**: "Name 4 planets in our solar system"
4. **Pop Culture**: "Name 5 Marvel superheroes"
5. **Multi Choice**: "List 3 programming languages"
6. **Scavenger Hunts**: "Find and name 5 types of trees in the park"

## Display Examples

### In `/current` command:
```
🎯 Your Current Challenge

Challenge #5: Capital Cities Challenge
❓ Type: multi_choice
📍 Location: Anywhere
📝 Name 5 capital cities from different continents

ℹ️ Reply with your answer.

📝 Checklist Items:
✅ Tokyo
✅ Paris
⬜ Cairo
⬜ Brasilia
⬜ Canberra

Progress: 2/5 items completed
💡 Tip: Submit each item individually or all at once!

💡 Hints available: 1
💡 Hints used: 0/1

Use /submit [answer] to submit this challenge.
```

### In `/challenges` command:
```
🎯 Challenges 🎯

✅ Find the Landmark
   Take a team photo with the city skyline

✅ Riddle Master
   I stand tall where knowledge flows...

🎯 Capital Cities Challenge (CURRENT)
   Name 5 capital cities from different continents
   📝 Checklist: 2/5 items completed

Use /current to see full details of your current challenge.
```

## Technical Details

### Matching Algorithm

- Items are matched case-insensitively using substring matching
- Items are found when they appear anywhere in the submitted text (e.g., "The capital is Tokyo" matches "Tokyo")
- Each item is matched independently - submitting "Tokyo and Paris" can match both items
- Each item is tracked independently in the team's state

### State Management

- Progress is saved per team per challenge
- Checklist state persists across bot restarts
- Duplicate submissions don't create errors (just show current progress)
- Progress resets when a new game starts

### Backward Compatibility

- Regular answer challenges continue to work as before
- Teams can use both checklist and regular challenges in the same game
- No changes needed to photo challenges or other verification methods

## Limitations

- Checklist items must be configured in advance
- Items cannot be added/removed during an active game
- The challenge only completes when all items are submitted (teams get progress tracking, but no partial completion)
- Checklist mode only works with `answer` verification method (not photos)

## Tips for Game Organizers

1. **Clear descriptions**: Make it obvious that participants should list multiple items
2. **Reasonable count**: 3-7 items works best for most challenges
3. **Distinct items**: Avoid items that are too similar or ambiguous
4. **Use hints**: Help teams who are stuck on the last few items
5. **Test beforehand**: Verify items match correctly with common phrasings

## Examples

See `config.example.yml` for a complete example of a checklist challenge configuration.
