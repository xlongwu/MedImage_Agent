const { spawn } = require("node:child_process");
const http = require("node:http");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const viteUrl = process.env.MEDIMAGE_DESKTOP_DEV_URL || "http://127.0.0.1:5173";
const children = [];
let shuttingDown = false;

function run(command, args, options = {}) {
  const child = spawn(command, args, {
    cwd: root,
    stdio: "inherit",
    shell: process.platform === "win32",
    windowsHide: true,
    ...options,
  });
  children.push(child);
  child.on("exit", (code) => {
    if (code && !shuttingDown) {
      shutdown(code);
    }
  });
  return child;
}

function waitForUrl(url, attempts = 60) {
  return new Promise((resolve, reject) => {
    let count = 0;
    const probe = () => {
      count += 1;
      const req = http.get(url, (res) => {
        res.resume();
        resolve();
      });
      req.on("error", () => {
        if (count >= attempts) {
          reject(new Error(`Timed out waiting for ${url}`));
          return;
        }
        setTimeout(probe, 500);
      });
      req.setTimeout(400, () => req.destroy(new Error("timeout")));
    };
    probe();
  });
}

function shutdown(code = 0) {
  shuttingDown = true;
  for (const child of children) {
    if (!child.killed) {
      child.kill();
    }
  }
  process.exit(code);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

async function main() {
  run("npm", ["run", "dev:renderer"]);
  await waitForUrl(viteUrl);
  run("npm", ["run", "dev:electron"], {
    env: {
      ...process.env,
      MEDIMAGE_DESKTOP_DEV_URL: viteUrl,
    },
  });
}

main().catch((error) => {
  console.error(error);
  shutdown(1);
});
