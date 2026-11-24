package com.drugtracker.app.data

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

class DrugRepository(private val context: Context) {

    private val prefs = context.getSharedPreferences("drug_tracker_prefs", Context.MODE_PRIVATE)
    private val cacheFile = File(context.filesDir, "cached_drugs.json")
    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    companion object {
        private const val KEY_FEED_URL = "feed_url"
        private const val KEY_GITHUB_TOKEN = "github_token"
        private const val KEY_BOOKMARKS = "bookmarks"
        private const val KEY_SEEN_EVENTS = "seen_events"
        private const val KEY_NOTIFICATIONS_ENABLED = "notifications_enabled"
        private const val KEY_NOTIFY_ONLY_NEW_INDICATIONS = "notify_only_new_indications"

        const val DEFAULT_FEED_URL =
            "https://raw.githubusercontent.com/torstendahlen/drug-approval-tracker/main/docs/data/drugs.json"
    }

    fun getFeedUrl(): String = prefs.getString(KEY_FEED_URL, DEFAULT_FEED_URL) ?: DEFAULT_FEED_URL

    fun setFeedUrl(url: String) {
        prefs.edit().putString(KEY_FEED_URL, url.trim()).apply()
    }

    fun getGithubToken(): String = prefs.getString(KEY_GITHUB_TOKEN, "") ?: ""

    fun setGithubToken(token: String) {
        prefs.edit().putString(KEY_GITHUB_TOKEN, token.trim()).apply()
    }

    fun isNotificationsEnabled(): Boolean = prefs.getBoolean(KEY_NOTIFICATIONS_ENABLED, true)

    fun setNotificationsEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_NOTIFICATIONS_ENABLED, enabled).apply()
    }

    fun isNotifyOnlyNewIndications(): Boolean = prefs.getBoolean(KEY_NOTIFY_ONLY_NEW_INDICATIONS, false)

    fun setNotifyOnlyNewIndications(onlyNewIndications: Boolean) {
        prefs.edit().putBoolean(KEY_NOTIFY_ONLY_NEW_INDICATIONS, onlyNewIndications).apply()
    }

    fun getBookmarks(): Set<String> = prefs.getStringSet(KEY_BOOKMARKS, emptySet())?.toSet() ?: emptySet()

    fun toggleBookmark(drugId: String): Set<String> {
        val updated = getBookmarks().toMutableSet()
        if (!updated.add(drugId)) {
            updated.remove(drugId)
        }
        prefs.edit().putStringSet(KEY_BOOKMARKS, updated).apply()
        return updated
    }

    fun getSeenEventKeys(): Set<String> = prefs.getStringSet(KEY_SEEN_EVENTS, emptySet())?.toSet() ?: emptySet()

    fun markEventsSeen(keys: Set<String>) {
        prefs.edit().putStringSet(KEY_SEEN_EVENTS, keys).apply()
    }

    fun eventKey(drugId: String, event: RegulatoryEvent): String =
        "$drugId|${event.source}|${event.date}|${event.title}"

    suspend fun loadCachedOrBundled(): DrugFeed = withContext(Dispatchers.IO) {
        val raw = if (cacheFile.exists()) {
            cacheFile.readText()
        } else {
            context.assets.open("sample_drugs.json").bufferedReader().use { it.readText() }
        }
        runCatching { json.decodeFromString<DrugFeed>(raw) }.getOrDefault(DrugFeed())
    }

    suspend fun refreshFromRemote(): Result<DrugFeed> = withContext(Dispatchers.IO) {
        val urlStr = getFeedUrl()
        val token = getGithubToken()

        runCatching {
            val conn = (URL(urlStr).openConnection() as HttpURLConnection).apply {
                connectTimeout = 15_000
                readTimeout = 30_000
                requestMethod = "GET"
                setRequestProperty("Accept", "application/json")
                if (token.isNotBlank()) {
                    setRequestProperty("Authorization", "Bearer $token")
                }
            }
            try {
                val code = conn.responseCode
                if (code == 404) {
                    error("HTTP 404: Check Feed URL or add GitHub Token in Settings if repo is private.")
                }
                if (code !in 200..299) {
                    error("HTTP $code from feed URL")
                }
                val body = conn.inputStream.bufferedReader().use { it.readText() }
                val parsed = json.decodeFromString<DrugFeed>(body)
                cacheFile.writeText(body)
                parsed
            } finally {
                conn.disconnect()
            }
        }
    }
}
