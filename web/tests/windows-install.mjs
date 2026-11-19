import { chromium, expect } from "@playwright/test";
import { preview } from "vite";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";
import { execFile } from "node:child_process";
const channel = process.argv[2],
    run = promisify(execFile);
if (process.platform !== "win32" || !["chrome", "msedge"].includes(channel))
    throw Error("Se necesita Chrome o Edge en Windows.");
const base = "http://127.0.0.1:4192/armario-digital/";
const root = await mkdtemp(join(tmpdir(), "ad-pwa-"));
const server = await preview({
    preview: { host: "127.0.0.1", port: 4192, strictPort: true },
});
let ctx,
    cdp,
    installed = false;
try {
    ctx = await chromium.launchPersistentContext(root, {
        channel,
        headless: false,
    });
    const page = await ctx.newPage();
    await page.goto(base);
    await page.bringToFront();
    await page.evaluate(() => navigator.serviceWorker.ready.then(() => true));
    cdp = await ctx.newCDPSession(page);
    await cdp.send("PWA.install", {
        manifestId: base,
        installUrlOrBundleUrl: base,
    });
    installed = true;
    await cdp.send("PWA.getOsAppState", { manifestId: base });
    await cdp.send("PWA.launch", { manifestId: base });
    const standalone = async () => {
        for (const p of ctx.pages()) {
            if (
                p.url().startsWith(base) &&
                (await p
                    .evaluate(
                        () => matchMedia("(display-mode: standalone)").matches,
                    )
                    .catch(() => false))
            )
                return p;
        }
    };
    await expect
        .poll(async () => !!(await standalone()), { timeout: 20000 })
        .toBe(true);
    const win = await standalone();
    await win.getByRole("button", { name: "Probar la demo" }).click();
    await expect(
        win.getByRole("heading", { name: "Camisa blanca" }),
    ).toBeVisible();
    console.log(
        channel,
        "instalación registrada y ventana independiente con catálogo y fotos, OK.",
    );
    await win.close();
    const powershell = `
    $ErrorActionPreference='Stop'
    $dirs=@([Environment]::GetFolderPath('DesktopDirectory'),[Environment]::GetFolderPath('Programs'))
    $shortcut=Get-ChildItem -LiteralPath $dirs -Filter '*Armario*.lnk' -Recurse | Select-Object -First 1
    if (!$shortcut) {throw 'No se ha encontrado el acceso directo instalado.'}
    Write-Output ('Acceso directo: '+$shortcut.Name)
    Start-Process -FilePath $shortcut.FullName
  `;
    const result = await run("powershell.exe", [
        "-NoProfile",
        "-Command",
        powershell,
    ]);
    console.log(result.stdout);
    await expect
        .poll(async () => !!(await standalone()), { timeout: 20000 })
        .toBe(true);
    console.log(
        channel,
        "acceso directo de Windows abrió la aplicación independiente.",
    );
} finally {
    if (installed)
        await cdp.send("PWA.uninstall", { manifestId: base }).catch(() => {});
    await ctx?.close();
    await server.close();
    await rm(root, {
        force: true,
        recursive: true,
        maxRetries: 5,
        retryDelay: 300,
    });
}
