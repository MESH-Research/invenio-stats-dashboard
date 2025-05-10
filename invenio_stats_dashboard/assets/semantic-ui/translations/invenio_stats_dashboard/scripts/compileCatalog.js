#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const MESSAGES_DIR = path.join(__dirname, '..', 'messages');
const LANGUAGES = ['en']; // Add more languages as needed

// Process each language
LANGUAGES.forEach(lang => {
  const langDir = path.join(MESSAGES_DIR, lang);
  const poFile = path.join(langDir, 'messages.po');
  const moFile = path.join(langDir, 'messages.mo');

  if (fs.existsSync(poFile)) {
    try {
      // Compile PO file to MO file
      execSync(`msgfmt -o ${moFile} ${poFile}`);
      console.log(`Successfully compiled ${poFile} to ${moFile}`);
    } catch (error) {
      console.error(`Error compiling PO file for ${lang}:`, error.message);
    }
  } else {
    console.warn(`No PO file found for ${lang}`);
  }
});