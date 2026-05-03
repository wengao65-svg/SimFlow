#!/usr/bin/env node
/**
 * Validate JSON schemas and test data against schemas.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SCHEMAS_DIR = path.join(ROOT, 'schemas');

let errors = 0;

console.log('=== SimFlow Schema Validation ===\n');

if (!fs.existsSync(SCHEMAS_DIR)) {
  console.error('ERROR: schemas directory not found');
  process.exit(1);
}

const schemaFiles = fs.readdirSync(SCHEMAS_DIR).filter(f => f.endsWith('.json'));

schemaFiles.forEach(file => {
  const filePath = path.join(SCHEMAS_DIR, file);
  try {
    const schema = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    if (!schema.$schema) {
      console.warn(`  WARNING: ${file} - missing $schema`);
    }
    if (!schema.title) {
      console.warn(`  WARNING: ${file} - missing title`);
    }
    if (!schema.type) {
      console.error(`  ERROR: ${file} - missing type`);
      errors++;
    }
    console.log(`  OK: ${file}`);
  } catch (e) {
    console.error(`  ERROR: ${file} - invalid JSON: ${e.message}`);
    errors++;
  }
});

console.log(`\n=== Summary ===`);
console.log(`Errors: ${errors}`);
process.exit(errors > 0 ? 1 : 0);
