const fs = require('fs');
const path = require('path');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

function findPluginManifest(root) {
  const candidates = [
    path.join(root, '.claude-plugin', 'plugin.json'),
    path.join(root, '.codex-plugin', 'plugin.json'),
    path.join(root, 'package.json'),
  ];
  return candidates.find(candidate => fs.existsSync(candidate));
}

function pluginVersionFromRoot(root) {
  const manifest = findPluginManifest(root);
  if (!manifest) {
    throw new Error(`No plugin manifest found under ${root}`);
  }
  const version = readJson(manifest).version;
  if (typeof version !== 'string' || version.length === 0) {
    throw new Error(`No plugin version found in ${manifest}`);
  }
  return version;
}

function skillNamesFromRoot(root) {
  const skillsRoot = path.join(root, 'skills');
  if (!fs.existsSync(skillsRoot)) {
    throw new Error(`No skills directory found under ${root}`);
  }
  return fs.readdirSync(skillsRoot)
    .filter(entry => fs.existsSync(path.join(skillsRoot, entry, 'SKILL.md')))
    .sort();
}

function parseSemver(version) {
  const match = String(version).match(/^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$/);
  if (!match) {
    throw new Error(`Invalid semantic version: ${version}`);
  }
  return match.slice(1, 4).map(Number);
}

function compareSemver(left, right) {
  const a = parseSemver(left);
  const b = parseSemver(right);
  for (let i = 0; i < 3; i += 1) {
    if (a[i] > b[i]) return 1;
    if (a[i] < b[i]) return -1;
  }
  return 0;
}

function diffSkillNames(currentSkills, previousSkills) {
  const current = new Set(currentSkills);
  const previous = new Set(previousSkills);
  return {
    added: currentSkills.filter(skill => !previous.has(skill)),
    removed: previousSkills.filter(skill => !current.has(skill)),
  };
}

function evaluateMarketplaceVersionGuard(current, previous) {
  const diff = diffSkillNames(current.skills, previous.skills);
  const skillsChanged = diff.added.length > 0 || diff.removed.length > 0;
  const versionIncreased = compareSemver(current.version, previous.version) > 0;
  return {
    ok: !skillsChanged || versionIncreased,
    skillsChanged,
    versionIncreased,
    diff,
  };
}

function guardRoots(currentRoot, previousRoot) {
  const current = {
    version: pluginVersionFromRoot(currentRoot),
    skills: skillNamesFromRoot(currentRoot),
  };
  const previous = {
    version: pluginVersionFromRoot(previousRoot),
    skills: skillNamesFromRoot(previousRoot),
  };
  return {
    current,
    previous,
    result: evaluateMarketplaceVersionGuard(current, previous),
  };
}

module.exports = {
  compareSemver,
  diffSkillNames,
  evaluateMarketplaceVersionGuard,
  guardRoots,
  pluginVersionFromRoot,
  skillNamesFromRoot,
};
