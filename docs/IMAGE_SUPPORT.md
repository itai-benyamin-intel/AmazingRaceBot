# Image Support Documentation

## Overview

The AmazingRaceBot now supports sending images to players as part of challenges and hints. This feature allows game organizers to create more engaging and visually rich experiences by including images in their challenges and hints.

## Features

### Challenge Images

Challenges can include an image that is displayed when the challenge is revealed to teams. This is useful for:

- Visual puzzles (e.g., "What landmark is this?")
- Photo-based questions
- Map or diagram challenges
- Visual clues

### Hint Images

Individual hints can have associated images that are sent when the hint is revealed. This provides:

- Visual hints that complement text hints
- Progressive visual clues
- Enhanced hint effectiveness

## Configuration

### Challenge Images

Add images to challenges using either `image_url` (for remote images) or `image_path` (for local images):

```yaml
challenges:
  - id: 1
    name: "Identify the Landmark"
    description: "What famous landmark is shown in this image?"
    location: "Anywhere"
    type: "riddle"
    verification:
      method: "answer"
      answer: "eiffel tower"
    # Remote image via HTTPS URL
    image_url: "https://example.com/landmark.jpg"
    # OR local image from images/ directory
    # image_path: "images/landmark.jpg"
```

### Hint Images

Add images to specific hints using the `hint_images` field with hint indices (0-based):

```yaml
challenges:
  - id: 2
    name: "Geography Challenge"
    description: "Name this capital city"
    location: "Anywhere"
    type: "riddle"
    verification:
      method: "answer"
      answer: "paris"
    hints:
      - "This city is in Europe"
      - "It's known for a famous tower"
      - "The city of lights"
    hint_images:
      0: "images/europe_map.jpg"      # Image for first hint (index 0)
      1: "https://example.com/tower.jpg"  # Image for second hint (index 1)
      # Hint 2 (index 2) has no image, just text
```

## Image Sources

### Remote Images (URLs)

- Must use HTTPS protocol (HTTP is rejected for security)
- Recommended for images hosted on image services (e.g., Imgur)
- Can include query parameters
- Example: `https://i.imgur.com/abc123.jpg`

**Trusted Domains** (allowed without file extension):
- `imgur.com`
- `i.imgur.com`
- `example.com` (for testing)

### Local Images (File Paths)

- Must be relative to the bot directory
- Recommended to store in the `images/` directory
- Supported formats: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- Example: `images/challenge1.png`

**Setting up local images:**

1. Create an `images/` directory in your bot folder:
   ```bash
   mkdir images
   ```

2. Place your image files in the directory:
   ```bash
   cp my_challenge_image.jpg images/
   ```

3. Reference them in your config:
   ```yaml
   image_path: "images/my_challenge_image.jpg"
   ```

## Security Features

The image support includes several security measures to protect your bot and server:

### URL Validation

- **HTTPS Only**: Only HTTPS URLs are accepted to prevent man-in-the-middle attacks
- **Domain Whitelisting**: Trusted domains are allowed even without file extensions
- **Extension Checking**: URLs are validated for image file extensions

### Path Validation

- **No Directory Traversal**: Paths like `../../../etc/passwd` are rejected
- **No Absolute Paths**: Paths like `/tmp/image.png` are rejected
- **Bot Directory Restriction**: All paths must be within the bot directory
- **File Existence**: Validates that the file exists before sending
- **Extension Validation**: Only image file extensions are allowed

### Error Handling

- Invalid images are logged but don't crash the bot
- If an image fails to send, the challenge/hint text is still sent
- Users receive the challenge/hint even if the image is unavailable

## Usage Examples

### Visual Puzzle Challenge

```yaml
- id: 1
  name: "What's This Place?"
  description: "Identify the landmark in this image"
  location: "Anywhere"
  type: "riddle"
  verification:
    method: "answer"
    answer: "big ben"
  image_url: "https://example.com/mystery_landmark.jpg"
  hints:
    - "It's in the United Kingdom"
    - "It's a famous clock tower"
```

### Map-Based Challenge

```yaml
- id: 2
  name: "Find the Route"
  description: "What is the shortest route shown in red?"
  location: "Campus"
  type: "riddle"
  verification:
    method: "answer"
    answer: "route a"
  image_path: "images/campus_map.png"
```

### Progressive Visual Hints

```yaml
- id: 3
  name: "Mystery Building"
  description: "Name this historic building"
  location: "Downtown"
  type: "riddle"
  verification:
    method: "answer"
    answer: "library"
  hints:
    - "Here's a zoomed-out view"
    - "Here's the front entrance"
    - "Here's the sign"
  hint_images:
    0: "images/building_wide.jpg"
    1: "images/building_front.jpg"
    2: "images/building_sign.jpg"
```

### Mixed Text and Image Hints

```yaml
- id: 4
  name: "Code Breaking"
  description: "Decode this cipher"
  location: "Anywhere"
  type: "decryption"
  verification:
    method: "answer"
    answer: "hello world"
  image_path: "images/cipher.png"
  hints:
    - "It's a Caesar cipher"  # Text-only hint
    - "Try a shift of 3"      # Text-only hint
    - "Here's the alphabet"   # This hint has an image
  hint_images:
    2: "images/alphabet_shift.jpg"
```

## Best Practices

### Image Selection

1. **Use appropriate file sizes**: Compress images to reduce bandwidth
2. **Choose clear images**: Ensure images are legible on mobile devices
3. **Test on mobile**: Most players will view on phones
4. **Consider accessibility**: Provide text descriptions in the challenge description

### Organization

1. **Use the images/ directory**: Keep all images organized in one place
2. **Use descriptive names**: Name files like `challenge1_landmark.jpg`
3. **Version control**: Commit images to your repository if using local files
4. **Backup remote images**: URLs can break, so have backups

### Security

1. **Use HTTPS only**: Never use HTTP URLs
2. **Verify image sources**: Only use trusted image hosting services
3. **Keep paths relative**: Always use paths relative to bot directory
4. **Check file sizes**: Large files can slow down the bot

### Testing

1. **Test before game day**: Verify all images load correctly
2. **Test on mobile**: Check image quality on phones
3. **Have fallbacks**: Ensure challenges work even if images fail
4. **Test with different teams**: Multiple concurrent image sends

## Troubleshooting

### Image Not Sending

**Check the logs** for error messages:
- `Invalid image URL`: URL doesn't use HTTPS or lacks proper extension
- `Invalid image path`: Path has directory traversal or is absolute
- `Image file not found`: Local file doesn't exist
- `Rejected image with unsupported extension`: File type not supported

**Common solutions:**
1. Verify HTTPS is used for URLs
2. Check that local file exists in the correct path
3. Ensure file extension is supported (.jpg, .jpeg, .png, .gif, .webp)
4. Verify path is relative (e.g., `images/file.jpg` not `/tmp/file.jpg`)

### Image Quality Issues

1. **Resize images** to reasonable dimensions (e.g., 1920x1080 max)
2. **Compress images** using tools like TinyPNG or ImageOptim
3. **Use JPEG for photos**, PNG for graphics with text
4. **Test on various devices** before the event

### Performance Issues

1. **Use remote URLs** for large images to save server resources
2. **Compress images** to reduce file size
3. **Limit simultaneous images** (avoid sending many large images at once)
4. **Monitor bot performance** during the event

## Implementation Details

### How It Works

1. **Challenge Broadcast**: When a challenge is broadcast, the bot:
   - Validates the image URL or path
   - Sends the image to each team member
   - Sends the challenge text separately

2. **Hint Reveal**: When a hint is revealed, the bot:
   - Checks if there's an image for that hint index
   - Validates the image configuration
   - Sends the image to the requesting user
   - Broadcasts the hint text to all team members

3. **Current Command**: When `/current` is used, the bot:
   - Checks if the current challenge has an image
   - Sends the image before the challenge details
   - Displays the full challenge text

### Technical Specifications

- **Supported Image Formats**: JPEG, PNG, GIF, WebP
- **URL Protocol**: HTTPS only
- **Path Restriction**: Within bot directory only
- **Max File Size**: Limited by Telegram API (typically 10MB for photos)
- **Concurrent Sends**: Handles multiple team members efficiently

## API Reference

### Configuration Fields

#### Challenge Level

- `image_url` (string, optional): HTTPS URL to remote image
- `image_path` (string, optional): Relative path to local image
- `hint_images` (dict, optional): Mapping of hint index to image path/URL

#### Example Structure

```yaml
challenges:
  - id: 1
    # ... other fields ...
    image_url: "https://example.com/image.jpg"
    # OR
    image_path: "images/local_image.png"
    # Hint images
    hint_images:
      0: "images/hint1.jpg"
      1: "https://example.com/hint2.jpg"
```

### Validation Rules

#### URL Validation
- Must start with `https://`
- Must end with image extension OR be from trusted domain
- Allowed extensions: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- Trusted domains: `imgur.com`, `i.imgur.com`, `example.com`

#### Path Validation
- Must not contain `..` (directory traversal)
- Must not start with `/` (absolute path)
- Must exist on filesystem
- Must have image extension
- Must resolve to path within bot directory

## FAQ

### Q: Can I mix remote and local images?

Yes! You can use `image_url` for some challenges and `image_path` for others. You can even mix them within `hint_images`.

### Q: What happens if an image fails to load?

The challenge or hint text is still sent to users. The bot logs the error but continues operating normally.

### Q: Can I change images after the game starts?

Yes, but players who have already received the challenge will see the old image. New players will see the new image.

### Q: Do images work with photo verification?

Yes! Challenge images are sent after photo verification is approved, ensuring images are only revealed when teams reach the location.

### Q: Can I use images from Google Images?

Be careful about copyright. It's better to use your own images or images from services like Unsplash, Pexels, or Pixabay that offer free images.

### Q: How do I know if my image URL will work?

Test it! Open the URL in a browser. If it shows the image directly (not a webpage with an image), it should work.

### Q: Is there a size limit?

Telegram limits photo sizes to 10MB. Keep images reasonable (under 5MB recommended) for best performance.

### Q: Can teams submit images as answers?

Yes, but that's a different feature (photo verification for challenges). This feature is for sending images TO teams, not receiving images FROM teams.

## Support

For issues or questions about image support:

1. Check the logs for error messages
2. Verify your configuration against the examples
3. Test with a small game before your event
4. Review the security validation rules

If you encounter bugs or have feature requests, please open an issue on the GitHub repository.
