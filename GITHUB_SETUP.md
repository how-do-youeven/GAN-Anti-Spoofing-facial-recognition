# GitHub Repository Setup Guide

Follow these steps to create a GitHub repository and upload your project.

## Step 1: Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the **"+"** icon in the top right → **"New repository"**
3. Fill in the repository details:
   - **Repository name**: `facial-recognition-login-system` (or your preferred name)
   - **Description**: "Facial recognition authentication system for student portal - FYP Project"
   - **Visibility**: Choose Public or Private
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
4. Click **"Create repository"**

## Step 2: Prepare Files for Upload

The project is already initialized with git. Now add all files:

```bash
cd /Users/timothypan/Desktop/school/FYP/FYP

# Add all files
git add .

# Check what will be committed
git status
```

## Step 3: Make Initial Commit

```bash
git commit -m "Initial commit: Facial recognition login system with BCE framework"
```

## Step 4: Connect to GitHub and Push

Replace `<your-username>` and `<repository-name>` with your actual GitHub username and repository name:

```bash
# Add remote repository
git remote add origin https://github.com/<your-username>/<repository-name>.git

# Rename main branch (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

**Example:**
```bash
git remote add origin https://github.com/johndoe/facial-recognition-login-system.git
git push -u origin main
```

## Step 5: Verify Upload

1. Go to your GitHub repository page
2. Verify all files are uploaded correctly
3. Check that README.md displays properly

## Important Notes

### Files NOT Uploaded (via .gitignore)

The following files are excluded for security and cleanliness:

- `venv/` - Virtual environment (users should create their own)
- `__pycache__/` - Python cache files
- `*.json` - Data files (user_accounts.json, known_faces.json, admin_config.json)
  - **Note**: These will be created automatically when users run the app
  - You may want to add example/empty versions if needed

### Sharing with Groupmates

1. **Share the repository URL** with your groupmates
2. They can clone it using:
   ```bash
   git clone https://github.com/<your-username>/<repository-name>.git
   ```
3. They should follow the installation steps in README.md

### Adding Collaborators

1. Go to your repository on GitHub
2. Click **"Settings"** → **"Collaborators"**
3. Click **"Add people"**
4. Enter your groupmates' GitHub usernames or emails
5. They'll receive an invitation to collaborate

## Troubleshooting

**If you get authentication errors:**
- Use GitHub Personal Access Token instead of password
- Or use SSH keys: `git@github.com:username/repo.git`

**If files are too large:**
- Check `.gitignore` is working
- Remove large files: `git rm --cached <file>`

**If you need to update later:**
```bash
git add .
git commit -m "Update: description of changes"
git push
```

## Next Steps

1. ✅ Create GitHub repository
2. ✅ Push code to GitHub
3. ✅ Share repository URL with groupmates
4. ✅ Add collaborators
5. ✅ Set up project board (optional)
6. ✅ Create issues for tasks (optional)

---

**Need Help?** Check GitHub's documentation: https://docs.github.com/en/get-started

