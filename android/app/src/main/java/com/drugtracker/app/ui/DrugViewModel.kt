package com.drugtracker.app.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.drugtracker.app.data.AtcGroupFilter
import com.drugtracker.app.data.DrugFeed
import com.drugtracker.app.data.DrugRecord
import com.drugtracker.app.data.DrugRepository
import com.drugtracker.app.data.SourceFilter
import com.drugtracker.app.data.UpdateTypeFilter
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class DrugUiState(
    val drugs: List<DrugRecord> = emptyList(),
    val generatedAt: String = "",
    val searchQuery: String = "",
    val sourceFilter: SourceFilter = SourceFilter.ALL,
    val updateTypeFilter: UpdateTypeFilter = UpdateTypeFilter.ALL,
    val atcFilter: AtcGroupFilter = AtcGroupFilter.ALL,
    val bookmarksOnly: Boolean = false,
    val bookmarks: Set<String> = emptySet(),
    val isRefreshing: Boolean = false,
    val statusMessage: String? = null,
    val feedUrl: String = "",
    val notificationsEnabled: Boolean = true,
    val notifyOnlyNewIndications: Boolean = false,
)

class DrugViewModel(application: Application) : AndroidViewModel(application) {

    private val repo = DrugRepository(application)

    private val _feed = MutableStateFlow(DrugFeed())
    private val _search = MutableStateFlow("")
    private val _source = MutableStateFlow(SourceFilter.ALL)
    private val _updateType = MutableStateFlow(UpdateTypeFilter.ALL)
    private val _atc = MutableStateFlow(AtcGroupFilter.ALL)
    private val _bookmarksOnly = MutableStateFlow(false)
    private val _bookmarks = MutableStateFlow(repo.getBookmarks())
    private val _isRefreshing = MutableStateFlow(false)
    private val _statusMessage = MutableStateFlow<String?>(null)
    private val _feedUrl = MutableStateFlow(repo.getFeedUrl())
    private val _notificationsEnabled = MutableStateFlow(repo.isNotificationsEnabled())
    private val _notifyOnlyIndications = MutableStateFlow(repo.isNotifyOnlyNewIndications())

    val uiState: StateFlow<DrugUiState> = combine(
        _feed,
        _search,
        _source,
        _updateType,
        _atc,
        _bookmarksOnly,
        _bookmarks,
        _isRefreshing,
        _statusMessage,
        _feedUrl,
        _notificationsEnabled,
        _notifyOnlyIndications,
    ) { values ->
        val feed = values[0] as DrugFeed
        val search = (values[1] as String).trim().lowercase()
        val source = values[2] as SourceFilter
        val updateType = values[3] as UpdateTypeFilter
        val atc = values[4] as AtcGroupFilter
        val bookmarksOnly = values[5] as Boolean
        @Suppress("UNCHECKED_CAST")
        val bookmarks = values[6] as Set<String>
        val isRefreshing = values[7] as Boolean
        val statusMsg = values[8] as String?
        val feedUrl = values[9] as String
        val notifEnabled = values[10] as Boolean
        val notifyOnlyInd = values[11] as Boolean

        val filtered = feed.drugs.filter { drug ->
            val matchesSource = source.code == null || drug.sourcesPresent.contains(source.code)
            val matchesType = updateType.code == null ||
                drug.latestUpdateType == updateType.code ||
                drug.events.any { it.updateType == updateType.code }
            val matchesAtc = atc.prefix == null ||
                drug.atcCode.startsWith(atc.prefix, ignoreCase = true)
            val matchesBookmark = !bookmarksOnly || drug.id in bookmarks
            val matchesSearch = search.isEmpty() ||
                drug.drugName.lowercase().contains(search) ||
                drug.activeSubstance.lowercase().contains(search) ||
                drug.atcCode.lowercase().contains(search) ||
                drug.therapeuticArea.lowercase().contains(search) ||
                drug.events.any {
                    it.indication.lowercase().contains(search) ||
                        it.title.lowercase().contains(search)
                }

            matchesSource && matchesType && matchesAtc && matchesBookmark && matchesSearch
        }

        DrugUiState(
            drugs = filtered,
            generatedAt = feed.generatedAt,
            searchQuery = values[1] as String,
            sourceFilter = source,
            updateTypeFilter = updateType,
            atcFilter = atc,
            bookmarksOnly = bookmarksOnly,
            bookmarks = bookmarks,
            isRefreshing = isRefreshing,
            statusMessage = statusMsg,
            feedUrl = feedUrl,
            notificationsEnabled = notifEnabled,
            notifyOnlyNewIndications = notifyOnlyInd,
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), DrugUiState())

    init {
        loadInitial()
    }

    private fun loadInitial() {
        viewModelScope.launch {
            val cached = repo.loadCachedOrBundled()
            _feed.value = cached
            if (repo.getSeenEventKeys().isEmpty()) {
                val keys = cached.drugs.flatMap { d -> d.events.map { repo.eventKey(d.id, it) } }.toSet()
                repo.markEventsSeen(keys)
            }
            refresh()
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _isRefreshing.value = true
            _statusMessage.value = null
            val result = repo.refreshFromRemote()
            result.onSuccess { feed ->
                _feed.value = feed
                val keys = feed.drugs.flatMap { d -> d.events.map { repo.eventKey(d.id, it) } }.toSet()
                repo.markEventsSeen(keys)
                _statusMessage.value = "Synced ${feed.counts.total} drugs"
            }.onFailure { err ->
                _statusMessage.value = err.message ?: "Offline · showing cached data"
            }
            _isRefreshing.value = false
        }
    }

    fun onSearchChange(q: String) { _search.value = q }
    fun onSourceFilterChange(f: SourceFilter) { _source.value = f }
    fun onUpdateTypeFilterChange(f: UpdateTypeFilter) { _updateType.value = f }
    fun onAtcFilterChange(f: AtcGroupFilter) { _atc.value = f }
    fun onBookmarksOnlyChange(only: Boolean) { _bookmarksOnly.value = only }
    fun toggleBookmark(drugId: String) { _bookmarks.value = repo.toggleBookmark(drugId) }
    fun clearStatusMessage() { _statusMessage.value = null }

    fun saveSettings(feedUrl: String, notificationsEnabled: Boolean, onlyNewIndications: Boolean) {
        repo.setFeedUrl(feedUrl)
        repo.setNotificationsEnabled(notificationsEnabled)
        repo.setNotifyOnlyNewIndications(onlyNewIndications)
        _feedUrl.value = repo.getFeedUrl()
        _notificationsEnabled.value = notificationsEnabled
        _notifyOnlyIndications.value = onlyNewIndications
        refresh()
    }
}
