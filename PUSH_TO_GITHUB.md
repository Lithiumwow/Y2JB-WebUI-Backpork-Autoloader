# Push to GitHub - Step by Step

## Step 1: Configure Git (First Time Only)

If you haven't configured git before, run these commands:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

Or for this repository only (without --global):

```bash
cd d:\Playstation5Backportproject\BackportLith\Y2JB-WebUI-Backpork-Autoloader
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

## Step 2: Commit Files

```bash
cd d:\Playstation5Backportproject\BackportLith\Y2JB-WebUI-Backpork-Autoloader

git commit -m "Initial commit: BackPork Autoloader integration for Y2JB-WebUI"
```

## Step 3: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `Y2JB-WebUI-Backpork-Autoloader`
3. Description: `BackPork integration module for Y2JB-WebUI - Automates PS5 game backporting`
4. Choose **Public** or **Private**
5. **DO NOT** check any boxes (no README, .gitignore, or license)
6. Click **"Create repository"**

## Step 4: Connect and Push

After creating the repository, GitHub will show you commands. Use these:

```bash
cd d:\Playstation5Backportproject\BackportLith\Y2JB-WebUI-Backpork-Autoloader

# Replace YOUR_USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR_USERNAME/Y2JB-WebUI-Backpork-Autoloader.git

git branch -M main

git push -u origin main
```

## Step 5: Verify

1. Go to your repository page on GitHub
2. You should see all files listed
3. The README.md will display automatically on the main page

## All-in-One Script

If you prefer, you can run this PowerShell script (replace YOUR_USERNAME, YOUR_NAME, and YOUR_EMAIL):

```powershell
cd d:\Playstation5Backportproject\BackportLith\Y2JB-WebUI-Backpork-Autoloader

# Configure git (replace with your info)
git config user.name "YOUR_NAME"
git config user.email "YOUR_EMAIL"

# Commit
git commit -m "Initial commit: BackPork Autoloader integration for Y2JB-WebUI"

# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/Y2JB-WebUI-Backpork-Autoloader.git

# Push
git branch -M main
git push -u origin main
```

## Troubleshooting

**If you get "remote origin already exists":**
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/Y2JB-WebUI-Backpork-Autoloader.git
```

**If push fails with authentication:**
- Use GitHub Personal Access Token instead of password
- Or use SSH: `git@github.com:YOUR_USERNAME/Y2JB-WebUI-Backpork-Autoloader.git`

**If you need to update later:**
```bash
git add .
git commit -m "Update description"
git push
```
