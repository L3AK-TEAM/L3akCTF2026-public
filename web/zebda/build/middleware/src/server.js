import express from 'express';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import yaml from 'js-yaml';

const __dirname = dirname(fileURLToPath(import.meta.url));

const app = express();
const port = Number(process.env.PORT ?? 8080);
const WORKER_URL = process.env.WORKER_URL ?? 'http://worker:8000';
const WORKER_TIMEOUT_MS = 8000;

app.disable('x-powered-by');

const projects = new Map();
const builds = new Map();

const reservedNames = new Set(['system', 'admin']);

function isReservedProjectName(slug) {
  return reservedNames.has(slug.toLowerCase());
}

const jsonBodyParser = express.json({ limit: '16kb' });
const yamlBodyParser = express.text({
  type: [
    'application/yaml',
    'application/x-yaml',
    'text/yaml',
    'text/plain',
  ],
  limit: '16kb',
});

function publicProject(project) {
  return { id: project.id, slug: project.slug, createdAt: project.createdAt };
}

function publicBuild(build) {
  return {
    id: build.id,
    projectId: build.projectId,
    status: build.status,
    artifact: build.artifact,
    logs: build.logs,
    createdAt: build.createdAt,
  };
}

function validateManifest(manifest) {
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
    throw new Error('Manifest must be an object');
  }
  if (!manifest.job || typeof manifest.job !== 'object') {
    throw new Error('Manifest must contain a job');
  }
  if (manifest.job.action !== 'translate') {
    throw new Error('Unsupported action');
  }
  if (typeof manifest.job.source !== 'string') {
    throw new Error('Source must be a string');
  }

  let sourceUrl;
  try {
    sourceUrl = new URL(manifest.job.source);
  } catch {
    throw new Error('Source must be a valid URL');
  }
  if (sourceUrl.protocol !== 'https:') {
    throw new Error('Only HTTPS sources are allowed');
  }
}

app.get('/health', (req, res) => {
  return res.json({
    message: 'App is pretty healthy and eating Koshary',
    service: 'middleware',
  });
});

app.post('/api/projects', jsonBodyParser, (req, res) => {
  const slug = req.body?.slug;
  if (typeof slug !== 'string' || slug.length === 0 || slug.length > 200) {
    return res.status(400).json({ error: 'slug must be a non-empty string' });
  }
  if (isReservedProjectName(slug)) {
    return res.status(403).json({ error: 'Reserved project name' });
  }

  const project = {
    id: randomUUID(),
    slug,
    createdAt: new Date().toISOString(),
  };
  projects.set(project.id, project);
  return res.status(201).json(publicProject(project));
});

app.get('/api/projects', (req, res) => {
  return res.json({ projects: [...projects.values()].map(publicProject) });
});

app.get('/api/projects/:projectId', (req, res) => {
  const project = projects.get(req.params.projectId);
  if (!project) {
    return res.status(404).json({ error: 'Project not found' });
  }
  return res.json(publicProject(project));
});

app.post('/api/projects/:projectId/builds', yamlBodyParser, async (req, res) => {
  const project = projects.get(req.params.projectId);
  if (!project) {
    return res.status(404).json({ error: 'Project not found' });
  }

  const rawManifest = req.body;
  if (typeof rawManifest !== 'string' || rawManifest.length === 0) {
    return res.status(400).json({ error: 'Manifest body is required' });
  }

  let parsedManifest;
  try {
    parsedManifest = yaml.load(rawManifest);
  } catch {
    return res.status(400).json({ error: 'Manifest is not valid YAML' });
  }

  try {
    validateManifest(parsedManifest);
  } catch (err) {
    return res.status(400).json({ error: err.message });
  }

  const build = {
    id: randomUUID(),
    projectId: project.id,
    status: 'pending',
    artifact: null,
    logs: [],
    createdAt: new Date().toISOString(),
  };
  builds.set(build.id, build);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), WORKER_TIMEOUT_MS);
  try {
    const workerResp = await fetch(`${WORKER_URL}/run`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ slug: project.slug, manifest: rawManifest }),
      signal: controller.signal,
    });

    const data = await workerResp.json().catch(() => ({}));
    if (workerResp.ok && data.ok) {
      build.status = 'success';
      build.artifact = data.artifact ?? null;
      build.logs = Array.isArray(data.logs) ? data.logs : [];
    } else {
      build.status = 'failed';
      build.logs = Array.isArray(data.logs) ? data.logs : [];
      if (data.error) build.logs.push(data.error);
    }
  } catch {
    build.status = 'failed';
    build.logs = ['Worker unavailable'];
  } finally {
    clearTimeout(timeout);
  }

  return res.status(201).json(publicBuild(build));
});

app.get('/api/builds/:buildId', (req, res) => {
  const build = builds.get(req.params.buildId);
  if (!build) {
    return res.status(404).json({ error: 'Build not found' });
  }
  return res.json(publicBuild(build));
});

app.use(express.static(join(__dirname, 'public')));

app.listen(port, '0.0.0.0');
