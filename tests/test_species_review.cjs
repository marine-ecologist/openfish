// Exercise staged review/download behavior without a browser dependency.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function element(value = '') { return {value, textContent: '', listeners: {}, addEventListener(type, callback) { this.listeners[type] = callback; }, click() { this.clicked = true; }}; }
const elements = {
  'species-data': {textContent: JSON.stringify({dataset_sha256: 'fixture', tracks: [{track_id: 1, species_id: 'unidentified'}]})},
  reviewer: element(), 'review-message': element(), 'download-reviews': element()
};
const select = element(); const note = element(); const state = element();
const button = element(); button.dataset = {track: '1'};
let downloaded;
vm.runInNewContext(fs.readFileSync('species_review.js', 'utf8'), {
  document: {
    getElementById: id => elements[id],
    querySelectorAll: () => [button],
    querySelector: selector => selector.startsWith('.species-choice') ? select : selector.startsWith('.review-note') ? note : state,
    createElement: () => element()
  },
  Blob: class { constructor(parts) { downloaded = JSON.parse(parts[0]); } },
  URL: {createObjectURL: () => 'blob:fixture', revokeObjectURL() {}},
  setTimeout: callback => callback(), Date
});
assert.equal(select.value, 'unidentified');
button.click = button.listeners.click;
button.click();
assert.match(elements['review-message'].textContent, /reviewer name/);
elements.reviewer.value = 'Reviewer';
select.value = 'a'; note.value = 'Markings'; button.click();
elements['download-reviews'].listeners.click();
assert.equal(downloaded.events.length, 1);
assert.equal(downloaded.events[0].species_id, 'a');
assert.equal(downloaded.events[0].note, 'Markings');
assert.equal(downloaded.dataset_sha256, 'fixture');
select.value = 'unidentified'; button.click();
elements['download-reviews'].listeners.click();
assert.equal(downloaded.events.length, 1);
assert.equal(downloaded.events[0].species_id, 'unidentified');
console.log('Species review controls passed');
