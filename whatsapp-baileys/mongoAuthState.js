import { MongoClient } from 'mongodb';
import {
  BufferJSON,
  initAuthCreds,
  proto,
} from '@whiskeysockets/baileys';

/**
 * Mongo-backed Baileys AuthenticationState.
 *
 * Credentials and Signal keys are stored as BufferJSON-serialized values. Use a
 * dedicated MongoDB user with access only to the Baileys auth database/collection.
 */
export async function useMongoAuthState({
  mongoUrl,
  dbName = 'foundations_baileys',
  sessionId = 'fca-primary',
}) {
  if (!mongoUrl) throw new Error('MONGO_URL is required for Mongo Baileys auth');

  const client = new MongoClient(mongoUrl, {
    serverSelectionTimeoutMS: 10000,
  });
  await client.connect();

  const collection = client.db(dbName).collection('baileys_auth_state');
  await collection.createIndex(
    { session_id: 1, auth_key: 1 },
    { unique: true, name: 'baileys_session_auth_key_unique' },
  );

  const serialize = (value) => JSON.stringify(value, BufferJSON.replacer);
  const deserialize = (value) => JSON.parse(value, BufferJSON.reviver);

  async function readData(authKey) {
    const doc = await collection.findOne(
      { session_id: sessionId, auth_key: authKey },
      { projection: { _id: 0, value: 1 } },
    );
    return doc?.value ? deserialize(doc.value) : null;
  }

  async function writeData(authKey, value) {
    await collection.updateOne(
      { session_id: sessionId, auth_key: authKey },
      {
        $set: {
          value: serialize(value),
          updated_at: new Date(),
        },
        $setOnInsert: {
          created_at: new Date(),
        },
      },
      { upsert: true },
    );
  }

  async function removeData(authKey) {
    await collection.deleteOne({ session_id: sessionId, auth_key: authKey });
  }

  const creds = (await readData('creds')) || initAuthCreds();

  const keys = {
    async get(type, ids) {
      const result = {};
      await Promise.all(ids.map(async (id) => {
        let value = await readData(`${type}:${id}`);
        if (type === 'app-state-sync-key' && value) {
          value = proto.Message.AppStateSyncKeyData.fromObject(value);
        }
        result[id] = value;
      }));
      return result;
    },

    async set(data) {
      const operations = [];
      for (const category of Object.keys(data || {})) {
        for (const id of Object.keys(data[category] || {})) {
          const value = data[category][id];
          const authKey = `${category}:${id}`;
          operations.push(value ? writeData(authKey, value) : removeData(authKey));
        }
      }
      await Promise.all(operations);
    },

    async clear() {
      await collection.deleteMany({ session_id: sessionId });
    },
  };

  return {
    state: { creds, keys },
    saveCreds: async () => writeData('creds', creds),
    close: async () => client.close(),
  };
}
