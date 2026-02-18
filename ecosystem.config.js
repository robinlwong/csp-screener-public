const path = require('path');
const fs = require('fs');

// --- UTILS ---
function parseEnv(content) {
  const result = {};
  content.split('\n').forEach(line => {
    line = line.trim();
    if (!line || line.startsWith('#')) return;
    const match = line.match(/^([\w.-]+)\s*=\s*(.*)?$/);
    if (match) {
      let key = match[1], value = match[2] || '';
      if (value.startsWith('"') && value.endsWith('"')) value = value.slice(1, -1);
      result[key] = value;
    }
  });
  return result;
}

function loadEnv(folderPath) {
  const envPath = path.resolve(folderPath, '.env');
  return fs.existsSync(envPath) ? parseEnv(fs.readFileSync(envPath, 'utf8')) : {};
}

// --- CONFIG FACTORY ---
const BROWSER_ARGS = "--no-sandbox,--disable-setuid-sandbox,--disable-dev-shm-usage,--disable-gpu,--remote-debugging-port=9222";
const CHROME_RELATIVE_PATH = "chrome/linux-145.0.7632.76/chrome-linux64/chrome";

/**
 * Creates a PM2 configuration object.
 * @param {string} name - Agent name (Jarvis, Marvin)
 * @param {number} port - Port number
 * @param {boolean} isAuthMode - If true, runs the interactive login command instead of the gateway
 */
function createAppConfig(name, port, isAuthMode = false) {
  const homeDir = `/home/ubuntu/.${name.toLowerCase()}`;
  const customEnv = loadEnv(homeDir);

  // Define the base config that both modes share
  const baseConfig = {
    name: isAuthMode ? `${name}-Auth` : name, // Naming convention: Marvin vs Marvin-Auth
    script: "/home/ubuntu/.local/share/pnpm/openclaw",
    interpreter: "bash",
    cwd: homeDir,
    // SHARED ENVIRONMENT VARIABLES
    env: {
      ...customEnv,
      OPENCLAW_HOME: homeDir,
      OPENCLAW_WORKSPACE: `${homeDir}/workspace`,
      OPENCLAW_CONFIG: `${homeDir}/.openclaw/config.json`,
      OPENCLAW_CONFIG_PATH: `${homeDir}/.openclaw/config.json`,
      OPENCLAW__GATEWAY__MODE: "local",
      
      // Models
      OPENCLAW_MODEL_ALIAS_ANTHROPIC__CLAUDE_SONNET_4_6: "anthropic/claude-sonnet-4-5",
      OPENCLAW_MODEL_ALIAS_GEMINI_FLASH: "google/gemini-3-flash-preview",
      OPENCLAW_MODEL_ALIAS_GEMINI_PRO: "google/gemini-3-pro-preview",
      OPENCLAW_MODEL_ALIAS_KIMI: "moonshot/kimi-k2.5",
      OPENCLAW_MODEL_ALIAS_MOONSHOT__KIMI_2___5: "moonshot/kimi-k2.5",

      // Lightweight Mode
      OPENCLAW__PLUGINS__SLOTS__MEMORY: "null",
      OPENCLAW__PLUGINS__ENTRIES__MEMORY_LANCEDB__ENABLED: "false",

      // WhatsApp Config (Crucial for Auth!)
      OPENCLAW__PLUGINS__ENTRIES__WHATSAPP__ENABLED: "true",
      OPENCLAW__PLUGINS__ENTRIES__WHATSAPP__CONFIG__AUTO_START: "true",
      OPENCLAW__PLUGINS__ENTRIES__WHATSAPP__CONFIG__SESSION_PATH: `${homeDir}/workspace`,

      // Browser
      OPENCLAW_BROWSER_EXECUTABLE_PATH: `${homeDir}/${CHROME_RELATIVE_PATH}`,
      OPENCLAW_BROWSER_ARGS: BROWSER_ARGS,
      OPENCLAW_MEMORY_PATH: `${homeDir}/workspace/data`,
      DEBUG: "openclaw:*"
    }
  };

  // MODE SWITCHING: Adjust args and PM2 behavior based on mode
  if (isAuthMode) {
    return {
      ...baseConfig,
      // Interactive login command
      args: ["channels", "login", "--channel", "whatsapp"], 
      autorestart: false, // Don't restart after login finishes
      watch: false        // Don't watch files
    };
  } else {
    return {
      ...baseConfig,
      // Standard gateway command
      args: ["gateway", "--port", port.toString(), "--force", "--allow-unconfigured"],
      autorestart: true,
      watch: false 
    };
  }
}

module.exports = {
  apps: [
    // --- MAIN AGENTS (Daemons) ---
    createAppConfig("Jarvis", 18789),
    createAppConfig("Marvin", 3001),

    // --- AUTH HELPERS (Interactive) ---
    // These share the exact same env/paths as above but run the login command
    createAppConfig("Jarvis", 18789, true),
    createAppConfig("Marvin", 3001, true)
  ]
};