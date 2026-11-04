// Exercise the generated gallery script with a minimal in-memory DOM.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.dataset = {}; }
  append(...nodes) {
    for (const node of nodes) {
      if (node.parent) node.parent.children.splice(node.parent.children.indexOf(node), 1);
      node.parent = this; this.children.push(node);
    }
  }
  replaceChildren() { for (const child of this.children) child.parent = null; this.children = []; }
}
const gallery = new Element('div');
const cards = [2, 3, 1, 4].map((id, i) => Object.assign(new Element('article'), {id, dataset: {group: [1, 2, 1, 0][i]}}));
const grid = new Element('div'); grid.append(...cards); gallery.append(grid);
gallery.querySelectorAll = () => cards;
let change;
const document = {getElementById: id => id === 'gallery' ? gallery : {addEventListener: (_, callback) => change = callback}, createElement: tag => new Element(tag)};
const page = fs.readFileSync(process.argv[2], 'utf8');
vm.runInNewContext(page.match(/<script>([\s\S]*?)<\/script>/)[1], {document});
for (let i = 0; i < 3; i++) {
  change({target: {value: 'similarity'}});
  assert.equal(gallery.children.length, 3);
  assert.deepEqual(gallery.children[0].children[1].children.map(c => c.id), [2, 1]);
  assert.equal(gallery.children[2].children[0].textContent, 'Ungrouped — embedding unavailable');
  change({target: {value: 'chronological'}});
  assert.deepEqual(gallery.children[0].children.map(c => c.id), [2, 3, 1, 4]);
}
console.log('Gallery sort switching passed (3 round trips; no cards lost).');
