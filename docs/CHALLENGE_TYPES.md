# Challenge Types Guide

This document provides detailed information about the challenge types system in the AmazingRaceBot.

## Overview

The challenge types system allows you to create diverse, engaging challenges with automatic verification. Each challenge type has specific characteristics and verification methods.

## Challenge Types

### 1. 📷 Photo Challenge

Teams take photos of specified objects, landmarks, or complete specific scenes.

**Configuration Example:**
```yaml
- id: 1
  name: "Team Photo at Landmark"
  description: "Take a team photo with the city skyline in the background"
  location: "Downtown Viewpoint"
  type: "photo"
  verification:
    method: "photo"
```

**How it works:**
- Teams use `/submit 1` to initiate submission
- Bot prompts them to send a photo
- Teams send the photo via Telegram
- Photo is sent to admin for approval
- Admin approves or rejects using inline buttons
- Challenge is marked complete after admin approval
- Team is notified of approval/rejection

**Use cases:**
- Team photos at specific locations
- Photos of completed puzzles
- Documentation of found items
- Creative team compositions

---

### 2. 🧩 Riddle/Clue Challenge

Teams solve riddles or puzzles to determine answers or next locations.

**Configuration Example:**
```yaml
- id: 2
  name: "Library Riddle"
  description: "I stand tall where knowledge flows, students gather in my shadow's throes. What am I?"
  location: "Campus"
  type: "riddle"
  verification:
    method: "answer"
    answer: "library"
```

**How it works:**
- Teams read the riddle in their challenge list
- They solve the riddle
- Use `/submit 2 library` to submit their answer
- Bot automatically verifies if the answer matches (case-insensitive)

**Answer matching:**
- Exact match: `library` = `library` ✅
- Case-insensitive: `LIBRARY` = `library` ✅
- Keyword match: `the library building` contains `library` ✅

---

### 3. 💻 Code Challenge

Teams write or debug code to solve a specific problem.

**Configuration Example (Recommended - Multiple Acceptable Answers):**
```yaml
- id: 3
  name: "Fibonacci Calculator"
  description: |
    Fix this Python function to correctly calculate Fibonacci numbers:
    
    def fib(n):
        if n <= 1:
            return 1  # Bug: should return n
        return fib(n-1) + fib(n-2)
    
    What should fib(5) return? Submit the correct result.
  location: "Computer Lab"
  type: "code"
  verification:
    method: "answer"
    # List multiple acceptable answer formats
    acceptable_answers:
      - "5"              # Just the number
      - "five"           # Written out
      - "answer is 5"    # In a sentence
```

**Configuration Example (Simple - Single Keyword):**
```yaml
- id: 3
  name: "Code Challenge"
  description: "Write a function called 'fibonacci' that calculates Fibonacci numbers."
  location: "Computer Lab"
  type: "code"
  verification:
    method: "answer"
    answer: "fibonacci"  # Checks if answer contains this keyword
```

**How it works:**
- Teams work on the coding problem
- Submit their answer using `/submit 3 <answer>`
- Bot verifies the submission against acceptable answers or keywords

**Verification Options:**

1. **Multiple Acceptable Answers** (Recommended for code challenges):
   ```yaml
   verification:
     method: "answer"
     acceptable_answers:
       - "42"
       - "forty-two"
       - "result: 42"
   ```
   - Accepts ANY one of the listed answers
   - Each answer can be an exact match OR contained in the submission
   - Case-insensitive matching
   - Best for code output verification

2. **Single Keyword** (Simple approach):
   ```yaml
   verification:
     method: "answer"
     answer: "fibonacci"
   ```
   - Checks if the keyword appears in the answer
   - Case-insensitive matching
   - Good for function names or simple validation

**Best Practices for Code Challenges:**
- **Ask for outputs**, not code: "What does this function return?" is easier to verify than code itself
- **Use acceptable_answers** for flexibility: Allow different formats (numeric, written, etc.)
- **Provide clear examples**: Show the exact input/output expected
- **Consider edge cases**: Include common variations in acceptable_answers
- **Test your verification**: Try different answer formats before the event

**Example Use Cases:**
1. **Bug Fix Challenge**: Find and fix a bug, submit the corrected output
2. **Algorithm Challenge**: Implement an algorithm, submit the result for a test case
3. **Code Reading**: Analyze code and predict the output
4. **Function Naming**: Write code with a specific function name (keyword verification)

---

### 4. 📱 QR Hunt Challenge

Teams find and scan hidden QR codes at locations.

**Configuration Example:**
```yaml
- id: 4
  name: "Hidden QR Code"
  description: "Find the QR code hidden near the water fountain"
  location: "Main Courtyard"
  type: "qr"
  verification:
    method: "answer"
    answer: "FOUNTAIN_2024"
```

**How it works:**
- Place QR codes containing specific text at locations
- Teams scan the QR code with any QR scanner app
- They submit the text from the QR code: `/submit 4 FOUNTAIN_2024`
- Bot verifies the code matches

**QR Code Setup:**
- Use online QR code generators
- Encode a unique text string for each location
- Print and place at challenge locations
- Update the `answer` field with the encoded text

---

### 5. ❓ Trivia Challenge

Teams answer questions related to specific topics.

**Configuration Example:**
```yaml
- id: 5
  name: "Tech Trivia"
  description: "Name three inventors who contributed to the development of the modern computer"
  location: "Anywhere"
  type: "trivia"
  verification:
    method: "answer"
    answer: "turing, lovelace, babbage"
```

**How it works:**
- Teams answer the trivia question
- Submit with `/submit 5 Alan Turing, Ada Lovelace, Charles Babbage`
- Bot checks if ALL required keywords are present in the answer

**Multiple keyword verification:**
- Answer must contain ALL keywords (comma-separated in config)
- Order doesn't matter
- Case-insensitive
- Example: `answer: "python, java, javascript"`
  - `"I know Python, JavaScript, and Java"` ✅
  - `"Python and Java"` ❌ (missing JavaScript)

---

### 6. 🔍 Scavenger Hunt Challenge

Teams find and document specific items.

**Configuration Example:**
```yaml
- id: 6
  name: "Transportation Hunt"
  description: "Find and photograph 5 different types of transportation in the area"
  location: "Campus Area"
  type: "scavenger"
  verification:
    method: "photo"
```

**How it works:**
- Teams search for the required items
- Take photos as proof
- Submit photo via `/submit 6` then send the photo
- Can be used for single items or collections

---

### 7. 🤝 Team Activity Challenge

Teams perform a specific activity together.

**Configuration Example:**
```yaml
- id: 7
  name: "Human Pyramid"
  description: "Create a human pyramid with your team"
  location: "Outdoor Area"
  type: "team_activity"
  verification:
    method: "photo"
```

**How it works:**
- Teams perform the activity together
- Take a photo as proof
- Submit via `/submit 7` then send the photo

**Activity ideas:**
- Human pyramids
- Group poses
- Synchronized actions
- Creative formations

---

### 8. 🔐 Decryption Challenge

Teams decrypt encoded messages.

**Configuration Example:**
```yaml
- id: 8
  name: "Caesar Cipher"
  description: "Decode this Caesar cipher (shift 3): Frqjudwxodwlrqv"
  location: "Anywhere"
  type: "decryption"
  verification:
    method: "answer"
    answer: "congratulations"
```

**How it works:**
- Teams receive an encoded message
- They decrypt it using the specified method
- Submit the decrypted message

**Encryption methods:**
- Caesar cipher (simple shift)
- Morse code
- Base64 encoding
- Custom ciphers

---

## Verification Methods

### Photo Verification

```yaml
verification:
  method: "photo"
```

- Teams submit photos via Telegram
- Photos are sent to admin for approval
- Admin receives photo with approve/reject buttons
- Challenge is marked complete after admin approval
- Team members are notified of approval/rejection

### Answer Verification

```yaml
verification:
  method: "answer"
  answer: "expected_answer"
```

**Single keyword:**
- Checks if the expected answer appears in the user's answer
- Case-insensitive matching
- Example: `answer: "keyboard"` matches "The answer is keyboard"

**Multiple keywords (trivia):**
- Use comma-separated keywords
- ALL keywords must be present in the user's answer
- Example: `answer: "python, java, javascript"`

## Best Practices

### Creating Effective Challenges

1. **Clear Instructions**: Make challenge descriptions clear and unambiguous
2. **Appropriate Difficulty**: Mix easy and hard challenges to keep teams engaged
3. **Variety**: Use different challenge types to keep the race interesting
4. **Testing**: Test your challenges before the event
5. **Backup Plans**: Have alternatives ready in case of technical issues

### Answer Configuration

1. **Use lowercase**: Always use lowercase in the `answer` field
2. **Simple answers**: Keep expected answers simple and clear
3. **Keywords**: For trivia, use distinctive keywords that are unlikely to appear by accident
4. **Test verification**: Test answer matching with various inputs

### Photo Challenges

1. **Specific requirements**: Be clear about what should be in the photo
2. **Safe locations**: Ensure photo locations are safe and accessible
3. **Legal considerations**: Ensure photos don't violate privacy or property rules
4. **Admin approval**: Admins must approve all photo submissions before challenges are marked complete
5. **Timely review**: Admins should review and approve/reject photos promptly to keep the game flowing

## Example Challenge Set

Here's a complete example of a diverse challenge set:

```yaml
challenges:
  # Easy starter
  - id: 1
    name: "Team Photo"
    description: "Take a team selfie at the starting point"
    location: "Registration Area"
    type: "photo"
    verification:
      method: "photo"
  
  # Medium riddle
  - id: 2
    name: "Where Am I?"
    description: "I have hands but cannot clap. What am I?"
    location: "Campus"
    type: "riddle"
    verification:
      method: "answer"
      answer: "clock"
  
  # Tech trivia
  - id: 3
    name: "Programming Languages"
    description: "Name three popular programming languages (comma-separated)"
    location: "Anywhere"
    type: "trivia"
    verification:
      method: "answer"
      answer: "python, java, javascript"
  
  # QR hunt
  - id: 4
    name: "Hidden Code"
    description: "Find the QR code at the library entrance"
    location: "Library"
    type: "qr"
    verification:
      method: "answer"
      answer: "LIBRARY_SECRET_2024"
  
  # Team activity
  - id: 5
    name: "Tower Challenge"
    description: "Build the tallest tower using provided materials and photograph it"
    location: "Activity Zone"
    type: "team_activity"
    verification:
      method: "photo"
  
  # Decryption
  - id: 6
    name: "Secret Message"
    description: "Decode: 01000110 01001001 01001110 01001001 01010011 01001000 (binary to ASCII)"
    location: "Anywhere"
    type: "decryption"
    verification:
      method: "answer"
      answer: "finish"
```

## Troubleshooting

### Teams can't submit answers
- Check that the game has started (`/startgame`)
- Verify they're submitting the current challenge (sequential order)
- Ensure answer format is correct

### Answer not being accepted
- Check for typos in the config `answer` field
- Remember answers are case-insensitive
- For trivia, ensure all keywords are present

### Photos not working
- Ensure teams send photos (not files or documents)
- Check that bot has permission to receive photos
- Verify network connectivity

## Future Enhancements

Potential additions to the challenge types system:

1. **Location Verification**: GPS-based automatic location checking
2. **Time Challenges**: Challenges that must be completed within a time limit
3. **Team Collaboration**: Challenges requiring multiple team submissions
4. **Puzzle Pieces**: Challenges that unlock parts of a larger puzzle
5. **Bonus Challenges**: Optional challenges for extra achievements
6. **Manual Approval**: Admin review workflow for subjective challenges

## Support

For questions or issues with challenge types:
- Check this documentation
- Review example configurations in `config.example.yml`
- Contact the bot admin using `/contact`
