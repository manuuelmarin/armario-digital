export async function testDirectory(context) {
    await context.addInitScript(() => {
        if (typeof FileSystemHandle === "undefined") return;
        FileSystemHandle.prototype.queryPermission = async () =>
            window.permissionState || "granted";
        FileSystemHandle.prototype.requestPermission = async () =>
            (window.permissionState = "granted");
        window.showDirectoryPicker = async () => {
            const path = window.testTarget || "Armario de prueba";
            if (window.cancelPicker)
                throw new DOMException("Cancelado", "AbortError");
            return (await navigator.storage.getDirectory()).getDirectoryHandle(
                path,
                { create: true },
            );
        };
    });
}
export async function openModules(page) {
    await page.goto("http://127.0.0.1:4174/armario-digital/tests/harness.html");
    await page.evaluate(async () => {
        const base = "/armario-digital/src/";
        window.modules = Object.assign(
            {},
            ...(await Promise.all(
                ["engine", "folder", "files", "backup", "media"].map(
                    (m) => import(base + m + ".js"),
                ),
            )),
        );
        window.directory = async (name) =>
            (await navigator.storage.getDirectory()).getDirectoryHandle(name, {
                create: true,
            });
    });
}
