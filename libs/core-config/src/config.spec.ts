import { MissingConfigError, readConfig } from './config';

describe('readConfig', () => {
  it('returns the values of the required variables when all are present', () => {
    const config = readConfig(['PORT', 'NAME'], { PORT: '3001', NAME: 'x' });

    expect(config).toEqual({ PORT: '3001', NAME: 'x' });
  });

  it('throws MissingConfigError naming the one missing variable', () => {
    expect(() => readConfig(['PORT'], {})).toThrow(MissingConfigError);
    expect(() => readConfig(['PORT'], {})).toThrow(/PORT/);
  });

  it('names every missing variable when several are missing', () => {
    let error: unknown;
    try {
      readConfig(['PORT', 'ALPHA', 'BETA'], { ALPHA: 'present' });
    } catch (e) {
      error = e;
    }

    expect(error).toBeInstanceOf(MissingConfigError);
    expect((error as MissingConfigError).missing).toEqual(['PORT', 'BETA']);
    expect((error as Error).message).toContain('PORT');
    expect((error as Error).message).toContain('BETA');
    expect((error as Error).message).not.toContain('ALPHA');
  });

  it('treats an empty value as missing', () => {
    expect(() => readConfig(['PORT'], { PORT: '' })).toThrow(/PORT/);
  });

  it('puts no configuration value in the error message', () => {
    let error: unknown;
    try {
      readConfig(['PORT', 'SECRET_TOKEN'], {
        SECRET_TOKEN: 's3cr3t-value-123',
      });
    } catch (e) {
      error = e;
    }

    expect((error as Error).message).not.toContain('s3cr3t-value-123');
  });
});
