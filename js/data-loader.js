/**
 * 数据加载器 - 加载、解密、缓存数据
 */
const DataLoader = (() => {
  const cache = {};

  async function load(name) {
    if (cache[name]) return cache[name];

    const password = Auth.getPassword();
    if (!password) return null;

    try {
      const resp = await fetch(`data/${name}.enc`);
      if (!resp.ok) throw new Error(`Failed to fetch ${name}.enc`);
      const encData = await resp.text();
      const jsonStr = await Auth.decryptData(encData, password);
      if (!jsonStr) throw new Error('Decrypt failed');
      const data = JSON.parse(jsonStr);
      cache[name] = data;
      return data;
    } catch (e) {
      console.error(`Load ${name} failed:`, e);
      return null;
    }
  }

  async function loadAll() {
    const names = ['projects', 'people', 'risks', 'timeline', 'feedback'];
    const results = await Promise.all(names.map(n => load(n)));
    const data = {};
    names.forEach((n, i) => { data[n] = results[i]; });
    return data;
  }

  function clearCache() {
    Object.keys(cache).forEach(k => delete cache[k]);
  }

  return { load, loadAll, clearCache };
})();
