import { test, expect } from "@playwright/test";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const WEB = path.join(ROOT, "web");

function contentType(file) {
  if (file.endsWith(".html")) return "text/html; charset=utf-8";
  if (file.endsWith(".js")) return "text/javascript; charset=utf-8";
  if (file.endsWith(".json")) return "application/json; charset=utf-8";
  return "application/octet-stream";
}

async function serveWeb() {
  const server = createServer(async (req, res) => {
    const url = new URL(req.url || "/", "http://127.0.0.1");
    const name = url.pathname === "/" ? "/index.html" : url.pathname;
    const file = path.normalize(path.join(WEB, name));
    if (!file.startsWith(WEB)) {
      res.writeHead(403);
      res.end("forbidden");
      return;
    }
    try {
      const data = await readFile(file);
      res.writeHead(200, { "content-type": contentType(file) });
      res.end(data);
    } catch {
      res.writeHead(404);
      res.end("not found");
    }
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  return {
    url: `http://127.0.0.1:${port}/`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

test("terminal page renders the fallback game and builds CLI commands", async ({ page }) => {
  const server = await serveWeb();
  try {
    await page.route("https://esm.sh/**", (route) => route.abort());
    await page.goto(server.url);

    await expect(page.locator("#source")).toHaveText("CONTRACT: SNAPSHOT");
    await expect(page.locator("#phase")).toHaveText("HELD");
    await expect(page.locator("#says")).toContainText("proposal #1 decides it");
    await expect(page.locator("#roster")).toContainText("Alice");
    await expect(page.locator("#queue")).toContainText("CLARIFICATION");
    await expect(page.locator("#log")).toContainText("UNDETERMINED");
    await expect(page.locator("#log")).toContainText("no rule");

    await page.getByRole("button", { name: /PF1 VOTE/ }).click();
    await expect(page.locator("#command")).toHaveText("python3 cli/nomic.py vote 1 yes");

    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: /PF2 RESOLVE/ }).click();
    await expect(page.locator("#command")).toHaveText("python3 cli/nomic.py resolve 1");

    await page.locator("#tabrules").click();
    await page.locator("#query").fill("immutable");
    await expect(page.locator("#rulelist")).toContainText("immutable");

    await page.locator("#tabdiff").click();
    await expect(page.locator("#diffhead")).toContainText("v1");
    await expect(page.locator("#diffchanges")).toContainText("GENESIS");
  } finally {
    await server.close();
  }
});
