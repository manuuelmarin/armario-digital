import { test } from "node:test";
import assert from "node:assert/strict";
import { models, chat, TEXT_MODEL, VISION_MODEL } from "../src/ollama.js";

test("Ollama usa únicamente el servidor local y detecta un cambio de modelo", async () => {
    const original = globalThis.fetch;
    const calls = [];
    let count = 0;
    globalThis.fetch = async (url, options) => {
        calls.push([url, options]);
        if (url.endsWith("/api/tags")) {
            count++;
            return Response.json({
                models: [{ name: TEXT_MODEL, digest: count === 1 ? "a" : "b" }],
            });
        }
        return Response.json({
            done: true,
            model: TEXT_MODEL,
            message: { content: "{}" },
        });
    };
    try {
        await assert.rejects(chat(TEXT_MODEL, "s", "u", {}), /cambiado/);
        assert.deepEqual(
            calls.map(([url]) => url),
            [
                "http://127.0.0.1:11434/api/tags",
                "http://127.0.0.1:11434/api/chat",
                "http://127.0.0.1:11434/api/tags",
            ],
        );
        assert.equal(calls[1][1].credentials, "omit");
        assert.equal(calls[1][1].redirect, "error");
        await assert.rejects(
            chat(TEXT_MODEL, "s", "u", {}, "foto"),
            /no admitidos/,
        );
    } finally {
        globalThis.fetch = original;
    }
});

test("Ollama identifica los modelos admitidos", async () => {
    const original = globalThis.fetch;
    globalThis.fetch = async () =>
        Response.json({
            models: [
                { name: VISION_MODEL, digest: "vision" },
                { name: "otro", digest: "otro" },
            ],
        });
    try {
        assert.deepEqual(await models(), { [VISION_MODEL]: "vision" });
    } finally {
        globalThis.fetch = original;
    }
});

test("Ollama rechaza dos versiones ambiguas del mismo modelo", async () => {
    const original = globalThis.fetch;
    globalThis.fetch = async () =>
        Response.json({
            models: [
                { name: TEXT_MODEL, digest: "uno" },
                { name: TEXT_MODEL, digest: "dos" },
            ],
        });
    try {
        await assert.rejects(models(), /duplicados/);
    } finally {
        globalThis.fetch = original;
    }
});
