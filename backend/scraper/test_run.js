const { execSync } = require('child_process');
const params = JSON.stringify({
  city: 'Lahore',
  dest_id: '-2767043',
  checkin: '2026-03-11',
  checkout: '2026-03-12',
  adults: 2,
  rooms: 1,
  children: 0,
  max_seconds: 60,
  max_results: 50,
});
console.log('Starting scraper test...');
console.log('Params:', params);
try {
  const result = execSync(`node puppeteer_scraper.js "${params.replace(/"/g, '\\"')}"`, {
    timeout: 60000,
    encoding: 'utf8',
    cwd: __dirname,
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  const data = JSON.parse(result);
  console.log('Success:', data.success);
  console.log('Hotels:', (data.hotels || []).length);
  console.log('Elapsed:', data.meta?.elapsed_seconds, 's');
  console.log('Combos run:', data.meta?.combos_run);
  if (data.hotels && data.hotels.length > 0) {
    console.log('First hotel:', data.hotels[0].name, '- PKR', data.hotels[0].price_per_night);
  }
} catch (e) {
  console.error('FAILED');
  if (e.stderr) console.error('stderr:', e.stderr.slice(-800));
  if (e.stdout) console.error('stdout:', e.stdout.slice(-300));
  console.error('Error:', e.message.slice(0, 200));
}
