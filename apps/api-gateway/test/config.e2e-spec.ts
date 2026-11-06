import { spawnSync } from 'node:child_process';
import { join } from 'node:path';

describe('api-gateway start-up configuration (e2e)', () => {
  it('exits non-zero and names the missing PORT without printing any value', () => {
    const main = join(
      __dirname,
      '../../../dist/apps/api-gateway/apps/api-gateway/src/main.js',
    );

    const result = spawnSync(process.execPath, [main], {
      env: { PATH: process.env.PATH, SECRET_TOKEN: 's3cr3t-value-123' },
      encoding: 'utf8',
      timeout: 20000,
    });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain('Missing required configuration: PORT');
    expect(result.stderr + result.stdout).not.toContain('s3cr3t-value-123');
  });
});
