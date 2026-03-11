const DataLoader = {
    _cache: {},
    _basePath: 'src/data/',

    setBasePath(path) {
        this._basePath = path;
    },

    async _fetchJSON(filename) {
        const url = this._basePath + filename;
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Failed to load ${filename}:`, error);
            throw error;
        }
    },

    async loadDoorOperators(useCache = true) {
        if (useCache && this._cache.doorOperators) {
            return this._cache.doorOperators;
        }
        const data = await this._fetchJSON('door-operators.json');
        if (useCache) {
            this._cache.doorOperators = data;
        }
        return data;
    },

    async loadTranslations(useCache = true) {
        if (useCache && this._cache.translations) {
            return this._cache.translations;
        }
        const data = await this._fetchJSON('translations.json');
        if (useCache) {
            this._cache.translations = data;
        }
        return data;
    },

    async loadBasicConfig(useCache = true) {
        if (useCache && this._cache.basicConfig) {
            return this._cache.basicConfig;
        }
        const data = await this._fetchJSON('basic-config.json');
        if (useCache) {
            this._cache.basicConfig = data;
        }
        return data;
    },

    async loadSpecialConfig(useCache = true) {
        if (useCache && this._cache.specialConfig) {
            return this._cache.specialConfig;
        }
        const data = await this._fetchJSON('special-config.json');
        if (useCache) {
            this._cache.specialConfig = data;
        }
        return data;
    },

    async loadParamMap(useCache = true) {
        if (useCache && this._cache.paramMap) {
            return this._cache.paramMap;
        }
        const data = await this._fetchJSON('param-map.json');
        if (useCache) {
            this._cache.paramMap = data;
        }
        return data;
    },

    async loadAll(useCache = true) {
        const [doorOperators, translations, basicConfig, specialConfig, paramMap] = await Promise.all([
            this.loadDoorOperators(useCache),
            this.loadTranslations(useCache),
            this.loadBasicConfig(useCache),
            this.loadSpecialConfig(useCache),
            this.loadParamMap(useCache)
        ]);

        return {
            doorOperators,
            translations,
            basicConfig,
            specialConfig,
            paramMap
        };
    },

    clearCache() {
        this._cache = {};
    },

    getCacheStatus() {
        return {
            doorOperators: !!this._cache.doorOperators,
            translations: !!this._cache.translations,
            basicConfig: !!this._cache.basicConfig,
            specialConfig: !!this._cache.specialConfig,
            paramMap: !!this._cache.paramMap
        };
    }
};

window.DataLoader = DataLoader;
