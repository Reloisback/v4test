# Discord Bot Documentation

## Main Menu Buttons

### 🏰 Alliance Operations
- Opens alliance management main menu
- Add, remove and edit alliances
- Configure alliance settings

### 👥 Member Operations
- Opens member management menu
- Add and view members
- Track member changes

### ⚙️ Bot Operations
- Opens bot settings and management menu
- Add/remove admins
- Configure log settings

### 🆘 Support Operations
- Opens support menu
- Help and developer information
- Direct contact options

### 🔧 Other Features
- Opens additional features menu
- Reserved for future updates

## Alliance Operations Menu

### ➕ Add Alliance
- Add new alliance
- Save alliance ID and name
- Configure initial settings

### 🗑️ Delete Alliance
- Remove existing alliance
- Clean up all related data
- Confirmation required

### 📊 View Alliances
- List all existing alliances
- Show member counts
- Display control intervals
- View alliance details

### ⚙️ Alliance Settings
- Configure alliance channels
- Set auto-check intervals
- Manage gift code settings

## Member Operations Menu

### ➕ Add Members
- Add new members to alliance
- Features:
  - Bulk member addition via FIDs
  - Real-time progress tracking
  - Rate limit handling (60s cooldown)
  - Success/Failure notifications
  - Automatic logging
- Logs stored in: `log/add_memberlog.txt`

### 📋 View Members
- List all alliance members
- Show member details:
  - Nickname
  - FID
  - Furnace level
  - Join date

## Gift Code Operations Menu

### 🎁 Use Gift Code
- Distribute gift codes to alliance members
- Features:
  - Automatic distribution
  - Real-time progress tracking
  - Status monitoring:
    - ✅ Success: Code redeemed
    - ⚠️ Already Used: Previously claimed
    - ❌ Failed: Error in redemption
  - Rate limit handling
  - Automatic logging
- Logs stored in: `log/giftlog.txt`

### 📊 Gift Code Status
- View gift code usage statistics
- Track successful redemptions
- Monitor failed attempts

## Support Menu

### 📝 Request Support
- Open support ticket
- Contact developer directly
- View help documentation

### 👨‍💻 Developer About
- Developer information
- Bot version details
- Support links

## Log System Menu

### 📝 Set Log Channel
- Configure logging channels
- Set up automatic notifications
- Choose log types

### 🗑️ Remove Log Channel
- Disable logging for channel
- Remove log settings

### 📊 View Log Channels
- List all logging channels
- Check log configurations

## Common Features

### Real-time Progress Tracking
- Live updates via embeds
- Color-coded status indicators:
  - 🔵 Blue: In Progress
  - 🟠 Orange: Rate Limited
  - 🟢 Green: Completed
  - 🔴 Red: Error

### Error Handling
- Rate limit detection
- API error management
- Database error handling
- User-friendly error messages

### Logging System
- Automatic log directory creation
- Detailed operation logs
- Timestamp tracking
- Success/Failure records

### Database Management
- Multiple SQLite databases:
  - alliance.sqlite: Alliance data
  - users.sqlite: Member information
  - settings.sqlite: Bot configuration
  - giftcode.sqlite: Gift code records
