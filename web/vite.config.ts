import { defineConfig } from 'vite'
import { createReadStream, statSync } from 'fs'
import { join, resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const pipelineData = resolve(__dirname, '../data')

export default defineConfig({
  plugins: [
    {
      // Serve ../data/* at /data/* in dev so both sample fixtures and real
      // pipeline output are accessible without copying files.
      name: 'pipeline-data',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const url = req.url ?? ''
          if (!url.startsWith('/data/')) return next()
          const rel = url.slice('/data'.length).split('?')[0]
          const filePath = join(pipelineData, rel)
          try {
            if (statSync(filePath).isFile()) {
              res.setHeader('Content-Type', 'application/json')
              res.setHeader('Cache-Control', 'no-cache')
              createReadStream(filePath).pipe(res as never)
              return
            }
          } catch {
            // not found — fall through to public/data/ fixtures
          }
          next()
        })
      },
    },
  ],
})
