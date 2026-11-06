import { NestFactory } from '@nestjs/core';
import { readConfigOrExit } from '@app/core-config';
import { AppModule } from './app.module';

async function bootstrap() {
  const { PORT } = readConfigOrExit(['PORT'], process.env);
  const app = await NestFactory.create(AppModule);
  await app.listen(PORT);
}
void bootstrap();
