// Gently Yonder — "Pick next pin + build query" (n8n Code node). Paste this
// whole file over the node's code, or re-import
// gentlyyonder-buffer-autopost.workflow.json.
//
// One fresh pin per run, oldest unsent first, and never the same pin twice:
//  - The old code wrapped around, so the 145 pins went out again every ~48
//    days. Pinterest rewards fresh pins (a new image) and repeated pins lose
//    reach. Those 145 now live in data/pins_posted_archive.json.
//  - Pins carry increasing ids (fresh ones start at 1001). We remember the last
//    id sent and take the next one above it. When the queue runs dry, nothing
//    is posted until generate_fresh_pins.py adds the next batch.
//  - Board ids come from pinterest.com/gentlyyonder (read 2026-09-27). A pin
//    whose board is not listed goes to Travel Packing Checklists.
const CHANNEL_ID = '6a47b7055ab6d2f1069dea9f';
const BOARDS = {
  'Travel Packing Checklists': '609956411972752122',
  'Asia Travel': '609956411972753421',
  'Language & Culture or Travel Reflections': '609956411972753420',
  'Travel Tech: eSIM & Insurance': '609956411972757874',
  'Japan Travel Guides': '609956411972750832',
  'Australia Travel Guides': '609956411972751419',
  'Vietnam Travel Guides': '609956411972750987',
};
const DEFAULT_BOARD = BOARDS['Travel Packing Checklists'];

const data = $input.first().json;
const pins = ((data && data.pins) || [])
  .filter(p => p && typeof p.id === 'number' && p.image && p.link)
  .sort((a, b) => a.id - b.id);

const store = $getWorkflowStaticData('global');
const lastId = typeof store.pinLastId === 'number' ? store.pinLastId : 1000;
const pin = pins.find(p => p.id > lastId);
if (!pin) { return []; }   // queue used up: post nothing rather than repeat
store.pinLastId = pin.id;

const query = 'mutation Create($input: CreatePostInput!) { createPost(input: $input) { __typename ... on PostActionSuccess { post { id } } ... on MutationError { message } } }';
const input = {
  text: String(pin.description || pin.title).slice(0, 500),
  channelId: CHANNEL_ID,
  schedulingType: 'automatic',
  mode: 'addToQueue',
  assets: [ { image: { url: pin.image } } ],
  metadata: { pinterest: {
    title: String(pin.title).slice(0, 100),
    url: pin.link,
    boardServiceId: BOARDS[pin.board] || DEFAULT_BOARD,
  } },
};

return [{ json: { channel: 'pinterest', pinId: pin.id, graphqlBody: { query, variables: { input } } } }];
