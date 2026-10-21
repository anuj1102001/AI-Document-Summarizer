import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// Point Tailwind at this folder's config explicitly, so it works however the dev server is launched.
const here = dirname(fileURLToPath(import.meta.url));

export default { plugins: { tailwindcss: { config: join(here, "tailwind.config.ts") }, autoprefixer: {} } };
