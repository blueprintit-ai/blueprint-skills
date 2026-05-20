# Contributing to BluePrint Skills

This guide outlines the workflow for adding new skills to the BluePrint Skills repository.

## 1. Setup

You should have already forked the repository and cloned it locally.

### Configure Remotes
Ensure you have both your fork (`origin`) and the main repository (`upstream`) configured:

```bash
# Add upstream if you haven't already
git remote add upstream https://github.com/blueprintit-ai/blueprint-skills.git

# Verify remotes
git remote -v
```

## 2. Syncing with Upstream

Before starting any new work, always sync with the main repository to avoid conflicts:

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

## 3. Creating a New Skill

Skills are located in the `shared-skills/` directory.

### Step 3.1: Create Skill Directory
Create a new directory for your skill:

```bash
mkdir shared-skills/<your-skill-name>
```

### Step 3.2: Create SKILL.md
Create a `SKILL.md` file inside your skill directory. This file instructs Claude on how to perform the skill.
See `shared-skills/video/SKILL.md` for a comprehensive example.

**Basic Structure:**
```markdown
---
name: <skill-name>
description: <short description>
---

# <Skill Title>

## Description
<Detailed description>

## How to use
<Instructions>
```

### Step 3.3: Register Your Skill
You must add your skill to the `.claude-plugin/skills-map.json` file.
Find the appropriate "department" (e.g., `marketing`, `sales`, `operations`) and add your skill to the `skills` object:

```json
"skills": {
  "your-skill-name": {
    "displayName": "My New Skill",
    "summary": "A brief summary of what this skill does"
  }
}
```

## 4. Generating the Plugin

Run the sync script to generate the plugin structure:

```bash
./sync-skills.sh
```

This script will:
1. Validates your configuration.
2. Copies your skill from `shared-skills/` to the appropriate `plugins/<department>/skills/` directory.
3. Regenerates the plugin manifests.

## 5. Testing and Submission Workflow

We use a two-step submission process to ensure quality.

### Step 5.1: Push to Development Repo (Testing)
First, push your changes to the development repository for testing.

```bash
# Add the development remote (one-time setup)
git remote add develop https://github.com/prabha-oss/blueprint-skills-develop.git

# Push your branch to develop
git push develop feature/your-skill-name
```

**Action**: Verify your skill in the test environment.

### Step 5.2: Push to Main Fork (Submission)
Once you have confirmed that your skill works as expected:

```bash
# Push to your main fork
git push origin feature/your-skill-name
```

Finally, open a Pull Request on GitHub from your fork (`origin`) to the main repository (`upstream`).
