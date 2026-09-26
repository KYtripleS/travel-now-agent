// Gently Yonder — "Pick next X post" (n8n Code node). Paste this whole file
// over the node's code, or re-import x-queue-autopost.workflow.json.
//
// One post per run, oldest unsent first, and never the same post twice:
//  - The old code wrapped around, so the 49-post queue went out two or three
//    times. X runs a duplicate-text job (botmaker rule BBQDuplicateTextProd)
//    that labels repeated text COPYPASTA_SPAM, which limits its reach.
//  - Posts carry increasing ids. We remember the last id sent and take the
//    next one above it. When the queue runs dry, nothing is posted until
//    site/data/x_queue.json is refilled. Refill, never recycle.
//  - No slicing: the old slice(0, 275) cut links in half. x_queue_check.py
//    keeps every post inside X's limit before it ships; anything longer
//    stops here with an error instead of going out broken.
//  - An optional "image" (an https://gentlyyonder.com/ URL) is attached.
const X_CHANNEL_ID = '6a47b8035ab6d2f1069def94';
const data = $input.first().json;
const posts = ((data && data.posts) || [])
  .filter(p => p && typeof p.id === 'number' && p.text)
  .sort((a, b) => a.id - b.id);

const store = $getWorkflowStaticData('global');
// ids 1-49 were the first queue, sent before this code; new posts start at 1001
const lastId = typeof store.xLastId === 'number' ? store.xLastId : 1000;
const post = posts.find(p => p.id > lastId);
if (!post) { return []; }   // queue used up: post nothing rather than repeat

const text = String(post.text);
if (text.length > 280) {
  throw new Error('X post ' + post.id + ' is ' + text.length + ' characters; fix site/data/x_queue.json');
}
store.xLastId = post.id;

const query = 'mutation Create($input: CreatePostInput!) { createPost(input: $input) { __typename ... on PostActionSuccess { post { id } } ... on MutationError { message } } }';
const input = {
  text,
  channelId: X_CHANNEL_ID,
  schedulingType: 'automatic',
  mode: 'addToQueue',
};
if (post.image) { input.assets = [ { image: { url: post.image } } ]; }

return [{ json: { channel: 'x', postId: post.id, graphqlBody: { query, variables: { input } } } }];
