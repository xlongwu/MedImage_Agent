const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const net = require("node:net");
const path = require("node:path");

const electronRoot = __dirname;
const repoRoot = path.resolve(electronRoot, "..", "..");

function binPath(root) {
  return path.join(
    root,
    "node_modules",
    ".bin",
    process.platform === "win32" ? "electron-builder.cmd" : "electron-builder"
  );
}

const localBuilder = binPath(electronRoot);
const frontendBuilder = binPath(path.join(repoRoot, "src", "frontend"));
const builder = fs.existsSync(localBuilder) ? localBuilder : frontendBuilder;

if (!fs.existsSync(builder)) {
  console.error("electron-builder was not found. Run npm install in desktop/electron first.");
  process.exit(1);
}

const electronCache = path.join(electronRoot, ".electron-cache");
const builderCache = path.join(electronRoot, ".electron-builder-cache");
const tempRoot = path.join(electronRoot, ".tmp");
const npmCache = path.join(electronRoot, ".npm-cache");
fs.mkdirSync(electronCache, { recursive: true });
fs.mkdirSync(builderCache, { recursive: true });
fs.mkdirSync(tempRoot, { recursive: true });
fs.mkdirSync(npmCache, { recursive: true });

const packageJson = require("./package.json");
const electronVersion = packageJson.devDependencies.electron;
const runtimeZipEnv = process.env.MEDIMAGE_ELECTRON_RUNTIME_ZIP;
const nsisArchiveEnv = process.env.MEDIMAGE_ELECTRON_NSIS_ARCHIVE;
const nsisResourcesArchiveEnv = process.env.MEDIMAGE_ELECTRON_NSIS_RESOURCES_ARCHIVE;
const extraArgs = process.argv.slice(2);

function hasElectronDistArg(args) {
  return args.some((arg) => arg === "--config.electronDist" || arg.startsWith("--config.electronDist="));
}

function sevenZipPath(root) {
  const arch = process.arch === "arm64" ? "arm64" : process.arch === "ia32" ? "ia32" : "x64";
  return path.join(root, "node_modules", "7zip-bin", "win", arch, "7za.exe");
}

function resolveSevenZip() {
  const local7za = sevenZipPath(electronRoot);
  const frontend7za = sevenZipPath(path.join(repoRoot, "src", "frontend"));
  const tool = fs.existsSync(local7za) ? local7za : frontend7za;
  if (!fs.existsSync(tool)) {
    console.error("7zip-bin was not found. Run npm install in src/frontend or desktop/electron first.");
    process.exit(1);
  }
  return tool;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function findAvailablePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : null;
      server.close(() => {
        if (port == null) {
          reject(new Error("Could not allocate local artifact server port."));
        } else {
          resolve(port);
        }
      });
    });
  });
}

async function startLocalBinariesServer(artifactDir) {
  const port = await findAvailablePort();
  const serverCode = [
    "const fs=require('node:fs');",
    "const http=require('node:http');",
    "const path=require('node:path');",
    "const root=process.argv[1];",
    "const port=Number(process.argv[2]);",
    "http.createServer((req,res)=>{",
    "  const url=new URL(req.url,'http://127.0.0.1');",
    "  const name=decodeURIComponent(url.pathname.slice(1));",
    "  if(!/^[A-Za-z0-9._-]+$/.test(name)){res.writeHead(404);res.end();return;}",
    "  const file=path.join(root,name);",
    "  const stream=fs.createReadStream(file);",
    "  stream.on('error',()=>{res.writeHead(404);res.end();});",
    "  stream.pipe(res);",
    "}).listen(port,'127.0.0.1');",
  ].join("");
  const child = spawn(process.execPath, ["-e", serverCode, artifactDir, String(port)], {
    cwd: electronRoot,
    stdio: "ignore",
    windowsHide: true,
  });
  await delay(500);
  return { child, url: `http://127.0.0.1:${port}` };
}

if (runtimeZipEnv && !hasElectronDistArg(extraArgs)) {
  const expectedZipName = `electron-v${electronVersion}-win32-x64.zip`;
  const sourceZip = path.resolve(runtimeZipEnv);
  const sourceStat = fs.existsSync(sourceZip) ? fs.statSync(sourceZip) : null;

  if (sourceStat == null || !sourceStat.isFile()) {
    console.error(`MEDIMAGE_ELECTRON_RUNTIME_ZIP does not point to a file: ${sourceZip}`);
    process.exit(1);
  }

  if (path.basename(sourceZip) !== expectedZipName) {
    console.error(`Expected Electron runtime zip ${expectedZipName}, got ${path.basename(sourceZip)}`);
    process.exit(1);
  }

  const runtimeCacheRelative = path.join(".electron-cache", "manual-runtime");
  const runtimeCache = path.join(electronRoot, runtimeCacheRelative);
  fs.mkdirSync(runtimeCache, { recursive: true });
  fs.copyFileSync(sourceZip, path.join(runtimeCache, expectedZipName));
  extraArgs.push(`--config.electronDist=${runtimeCacheRelative}`);
  console.log(`Using local Electron runtime zip: ${sourceZip}`);
}

let nsisDir = process.env.ELECTRON_BUILDER_NSIS_DIR;
if (nsisArchiveEnv && !nsisDir) {
  const expectedNsisName = "nsis-3.0.4.1.7z";
  const sourceArchive = path.resolve(nsisArchiveEnv);
  const sourceStat = fs.existsSync(sourceArchive) ? fs.statSync(sourceArchive) : null;

  if (sourceStat == null || !sourceStat.isFile()) {
    console.error(`MEDIMAGE_ELECTRON_NSIS_ARCHIVE does not point to a file: ${sourceArchive}`);
    process.exit(1);
  }

  if (path.basename(sourceArchive) !== expectedNsisName) {
    console.error(`Expected NSIS archive ${expectedNsisName}, got ${path.basename(sourceArchive)}`);
    process.exit(1);
  }

  nsisDir = path.join(builderCache, "manual-nsis", "nsis-3.0.4.1");
  const makensis = path.join(nsisDir, "makensis.exe");
  const elevate = path.join(nsisDir, "elevate.exe");

  if (!fs.existsSync(makensis) || !fs.existsSync(elevate)) {
    fs.mkdirSync(nsisDir, { recursive: true });
    const result = spawnSync(resolveSevenZip(), ["x", sourceArchive, `-o${nsisDir}`, "-y"], {
      cwd: electronRoot,
      stdio: "inherit",
      shell: false,
    });
    if (result.status !== 0) {
      console.error(`Failed to extract local NSIS archive: ${sourceArchive}`);
      process.exit(result.status ?? 1);
    }
  }

  if (!fs.existsSync(makensis) || !fs.existsSync(elevate)) {
    console.error(`Extracted NSIS archive is missing makensis.exe or elevate.exe: ${nsisDir}`);
    process.exit(1);
  }

  console.log(`Using local NSIS archive: ${sourceArchive}`);
}

async function main() {
  let localBinariesServer = null;
  const builderEnv = {
    ...process.env,
    ELECTRON_CACHE: electronCache,
    ELECTRON_BUILDER_CACHE: builderCache,
    TEMP: tempRoot,
    TMP: tempRoot,
    TMPDIR: tempRoot,
    NPM_CONFIG_CACHE: npmCache,
    npm_config_cache: npmCache,
    ...(nsisDir ? { ELECTRON_BUILDER_NSIS_DIR: nsisDir } : {}),
  };

  if (nsisResourcesArchiveEnv && !builderEnv.ELECTRON_BUILDER_BINARIES_DOWNLOAD_OVERRIDE_URL) {
    const expectedResourcesName = "nsis-resources-3.4.1.7z";
    const sourceArchive = path.resolve(nsisResourcesArchiveEnv);
    const sourceStat = fs.existsSync(sourceArchive) ? fs.statSync(sourceArchive) : null;

    if (sourceStat == null || !sourceStat.isFile()) {
      console.error(`MEDIMAGE_ELECTRON_NSIS_RESOURCES_ARCHIVE does not point to a file: ${sourceArchive}`);
      process.exit(1);
    }

    if (path.basename(sourceArchive) !== expectedResourcesName) {
      console.error(`Expected NSIS resources archive ${expectedResourcesName}, got ${path.basename(sourceArchive)}`);
      process.exit(1);
    }

    const localBinaries = path.join(builderCache, "manual-binaries");
    fs.mkdirSync(localBinaries, { recursive: true });
    fs.copyFileSync(sourceArchive, path.join(localBinaries, expectedResourcesName));
    localBinariesServer = await startLocalBinariesServer(localBinaries);
    builderEnv.ELECTRON_BUILDER_BINARIES_DOWNLOAD_OVERRIDE_URL = localBinariesServer.url;
    console.log(`Using local NSIS resources archive: ${sourceArchive}`);
  }

  const args = ["--config", "electron-builder.yml", ...extraArgs];
  const result = spawnSync(builder, args, {
    cwd: electronRoot,
    env: builderEnv,
    stdio: "inherit",
    shell: process.platform === "win32",
  });

  if (localBinariesServer) {
    localBinariesServer.child.kill();
  }

  process.exit(result.status ?? 1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
