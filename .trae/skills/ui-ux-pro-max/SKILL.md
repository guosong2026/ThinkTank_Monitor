---
name: "ui-ux-pro-max"
description: "Automates installation of UI/UX Pro Max tools including uipro-cli, project setup, and TRAE binding for UI beautification. Invoke when user wants to set up UI/UX tools for project enhancement."
---

# UI/UX Pro Max Skill

This skill automates the installation and setup of UI/UX Pro Max tools for enhancing the user interface of ThinkTank_Monitor project. It installs the necessary CLI tools, sets up the project environment, and binds TRAE for UI beautification.

## Quick Start

To set up the UI/UX Pro Max environment:

1. Ensure Node.js is installed and in your system PATH
2. Run the installation script:
   ```powershell
   .\scripts\install-ui-ux.ps1
   ```
3. After successful installation, invoke this skill to begin UI beautification

## Installation Steps

When invoked, this skill will perform the following steps:

### 1. Install Global uipro-cli Tool
Installs the uipro-cli globally via npm for UI/UX enhancement tools.

### 2. Navigate to Project Directory
Ensures the current working directory is the ThinkTank_Monitor project root.

### 3. Initialize and Bind TRAE
Sets up the project with TRAE integration for UI/UX enhancements.

### 4. Configure UI/UX Settings
Applies initial UI/UX configuration for the ThinkTank_Monitor system.

## Usage

After installation, the user can invoke UI/UX enhancement commands through:
- `uipro-cli` commands for UI improvements
- TRAE integration for automated UI beautification
- Built-in UI enhancement tools for ThinkTank_Monitor

## Dependencies

- Node.js (already installed as per user)
- npm package manager
- Internet connection for package downloads

## Notes

- This skill assumes Node.js is already installed on the system
- The skill will work in the current ThinkTank_Monitor project directory
- UI/UX enhancements may require project-specific configurations