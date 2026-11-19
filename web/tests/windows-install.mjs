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
        viewport: null,
    });
    ctx.setDefaultTimeout(20000);
    ctx.setDefaultNavigationTimeout(20000);
    const page = await ctx.newPage();
    await page.goto(base);
    await page.bringToFront();
    await page.waitForFunction(() => !!navigator.serviceWorker.controller);
    console.log("Service worker activo. Instalando desde el manifiesto.");
    cdp = await ctx.newCDPSession(page);
    await cdp.send("PWA.install", {
        manifestId: base,
        installUrlOrBundleUrl: base,
    });
    installed = true;
    await cdp.send("PWA.getOsAppState", { manifestId: base });
    await cdp.send("PWA.changeAppUserSettings", {
        manifestId: base,
        displayMode: "standalone",
    });
    const browser = await ctx.browser().newBrowserCDPSession();
    const launch = await cdp.send("PWA.launch", { manifestId: base });
    const info = await browser.send("Target.getTargetInfo", {
        targetId: launch.targetId,
    });
    console.log("Destino de la ventana instalada:", info.targetInfo);
    // PWA windows can belong to a browser context distinct from Playwright's page list.
    async function inspectWindow(targetId, expression) {
        const { sessionId } = await browser.send("Target.attachToTarget", {
            targetId,
            flatten: false,
        });
        let listener, timer;
        try {
            const answer = new Promise((ok, fail) => {
                timer = setTimeout(
                    () => fail(Error("Sin respuesta de la ventana instalada")),
                    5000,
                );
                listener = (event) => {
                    if (event.sessionId !== sessionId) return;
                    const m = JSON.parse(event.message);
                    if (m.id === 1) {
                        if (m.error || m.result?.exceptionDetails)
                            fail(Error(JSON.stringify(m)));
                        else ok(m.result.result.value);
                    }
                };
                browser.on("Target.receivedMessageFromTarget", listener);
            });
            await browser.send("Target.sendMessageToTarget", {
                sessionId,
                message: JSON.stringify({
                    id: 1,
                    method: "Runtime.evaluate",
                    params: {
                        expression,
                        returnByValue: true,
                        awaitPromise: true,
                    },
                }),
            });
            return await answer;
        } finally {
            clearTimeout(timer);
            if (listener)
                browser.off("Target.receivedMessageFromTarget", listener);
            await browser
                .send("Target.detachFromTarget", { sessionId })
                .catch(() => {});
        }
    }
    const snapshot = `({url:location.href,mode:matchMedia('(display-mode: standalone)').matches,title:document.title,screen:[innerWidth,innerHeight]})`;
    console.log(
        "Estado de la ventana:",
        await inspectWindow(launch.targetId, snapshot),
    );
    await expect
        .poll(
            async () => (await inspectWindow(launch.targetId, snapshot)).mode,
            { timeout: 12000 },
        )
        .toBe(true);
    await expect
        .poll(() =>
            inspectWindow(
                launch.targetId,
                "Array.from(document.querySelectorAll('button')).some(b=>b.textContent==='Probar la demo')",
            ),
        )
        .toBe(true);
    await inspectWindow(
        launch.targetId,
        "Array.from(document.querySelectorAll('button')).find(b=>b.textContent==='Probar la demo').click();true",
    );
    await expect
        .poll(() =>
            inspectWindow(
                launch.targetId,
                "document.body.innerText.includes('Camisa blanca')",
            ),
        )
        .toBe(true);
    console.log(
        channel,
        "instalación y ventana independiente con catálogo ficticio: OK.",
    );
    await browser.send("Target.closeTarget", { targetId: launch.targetId });
    const before = new Set(
        (await browser.send("Target.getTargets")).targetInfos.map(
            (t) => t.targetId,
        ),
    );
    const powershell = `
    $ErrorActionPreference='Stop'
    $dirs=@([Environment]::GetFolderPath('DesktopDirectory'),[Environment]::GetFolderPath('Programs'))
    $shortcut=Get-ChildItem -LiteralPath $dirs -Filter '*Armario*.lnk' -Recurse | Select-Object -First 1
    if (!$shortcut) {throw 'No se ha encontrado el acceso directo instalado.'}
    Write-Output ('Acceso directo: '+$shortcut.Name)
    $shell=New-Object -ComObject WScript.Shell
    Write-Output ($shell.CreateShortcut($shortcut.FullName).Arguments)
    Start-Process -FilePath $shortcut.FullName
  `;
    const result = await run("powershell.exe", [
        "-NoProfile",
        "-Command",
        powershell,
    ]);
    console.log(result.stdout);
    await expect
        .poll(
            async () => {
                const { targetInfos } = await browser.send("Target.getTargets");
                for (const target of targetInfos.filter(
                    (t) => !before.has(t.targetId) && t.url.startsWith(base),
                )) {
                    if ((await inspectWindow(target.targetId, snapshot)).mode)
                        return true;
                }
                return false;
            },
            { timeout: 20000 },
        )
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
