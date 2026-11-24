package com.drugtracker.app.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.BookmarkBorder
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.drugtracker.app.data.AtcGroupFilter
import com.drugtracker.app.data.DrugRecord
import com.drugtracker.app.data.SourceFilter
import com.drugtracker.app.data.TimeRangeFilter
import com.drugtracker.app.data.UpdateTypeFilter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(vm: DrugViewModel = viewModel()) {
    val state by vm.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    var selectedDrug by remember { mutableStateOf<DrugRecord?>(null) }
    var showSettings by remember { mutableStateOf(false) }

    LaunchedEffect(state.statusMessage) {
        state.statusMessage?.let { msg ->
            snackbarHostState.showSnackbar(msg)
            vm.clearStatusMessage()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Drug Approval Tracker", fontWeight = FontWeight.Bold)
                        Text(
                            text = "EMA · TLV · NT-rådet · ${state.drugs.size}/${state.totalInFeed} drugs",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { vm.refresh() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Sync now")
                    }
                    IconButton(onClick = { showSettings = true }) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings")
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (state.isRefreshing) {
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }

            OutlinedTextField(
                value = state.searchQuery,
                onValueChange = vm::onSearchChange,
                placeholder = { Text("Search drug, substance, ATC, indication...") },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                trailingIcon = {
                    if (state.searchQuery.isNotEmpty()) {
                        IconButton(onClick = { vm.onSearchChange("") }) {
                            Icon(Icons.Default.Clear, contentDescription = "Clear")
                        }
                    }
                },
                singleLine = true,
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
            )

            // Source, Time Range & Bookmarks row
            Row(
                modifier = Modifier
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                SourceFilter.entries.forEach { src ->
                    FilterChip(
                        selected = state.sourceFilter == src,
                        onClick = { vm.onSourceFilterChange(src) },
                        label = { Text(src.label) },
                    )
                }
                TimeRangeFilter.entries.forEach { range ->
                    FilterChip(
                        selected = state.timeRangeFilter == range,
                        onClick = { vm.onTimeRangeFilterChange(range) },
                        label = { Text(range.label) },
                    )
                }
                FilterChip(
                    selected = state.bookmarksOnly,
                    onClick = { vm.onBookmarksOnlyChange(!state.bookmarksOnly) },
                    leadingIcon = {
                        Icon(
                            imageVector = if (state.bookmarksOnly) Icons.Default.Bookmark else Icons.Default.BookmarkBorder,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp),
                        )
                    },
                    label = { Text("Saved (${state.bookmarks.size})") },
                )
            }

            // Update type & ATC row
            Row(
                modifier = Modifier
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                UpdateTypeFilter.entries.forEach { type ->
                    FilterChip(
                        selected = state.updateTypeFilter == type,
                        onClick = { vm.onUpdateTypeFilterChange(type) },
                        label = { Text(type.label) },
                    )
                }
                AtcGroupFilter.entries.forEach { atc ->
                    FilterChip(
                        selected = state.atcFilter == atc,
                        onClick = { vm.onAtcFilterChange(atc) },
                        label = { Text(atc.label) },
                    )
                }
            }

            if (state.drugs.isEmpty()) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = "No matching approvals or indications found.",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(state.drugs, key = { it.id }) { drug ->
                        DrugCard(
                            drug = drug,
                            isBookmarked = drug.id in state.bookmarks,
                            onToggleBookmark = { vm.toggleBookmark(drug.id) },
                            onClick = { selectedDrug = drug },
                        )
                    }
                }
            }
        }
    }

    selectedDrug?.let { drug ->
        DrugDetailSheet(
            drug = drug,
            isBookmarked = drug.id in state.bookmarks,
            onToggleBookmark = { vm.toggleBookmark(drug.id) },
            onDismiss = { selectedDrug = null },
        )
    }

    if (showSettings) {
        SettingsDialog(
            currentUrl = state.feedUrl,
            currentToken = state.githubToken,
            notificationsEnabled = state.notificationsEnabled,
            onlyNewIndications = state.notifyOnlyNewIndications,
            onDismiss = { showSettings = false },
            onSave = { url, token, notif, onlyInd ->
                vm.saveSettings(url, token, notif, onlyInd)
                showSettings = false
            },
        )
    }
}

@Composable
private fun DrugCard(
    drug: DrugRecord,
    isBookmarked: Boolean,
    onToggleBookmark: () -> Unit,
    onClick: () -> Unit,
) {
    val latestEvent = drug.events.firstOrNull()

    Card(
        shape = RoundedCornerShape(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = drug.drugName,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    if (drug.activeSubstance.isNotBlank()) {
                        Text(
                            text = drug.activeSubstance,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                IconButton(onClick = onToggleBookmark) {
                    Icon(
                        imageVector = if (isBookmarked) Icons.Default.Bookmark else Icons.Default.BookmarkBorder,
                        contentDescription = "Bookmark",
                        tint = if (isBookmarked) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            Row(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                UpdateTypeBadge(drug.latestUpdateType)
                drug.sourcesPresent.forEach { src ->
                    TagChip(label = sourceLabelFor(src), color = sourceColorFor(src))
                }
                if (drug.atcCode.isNotBlank()) {
                    TagChip(label = drug.atcCode, color = MaterialTheme.colorScheme.secondary)
                }
            }

            if (latestEvent != null) {
                Spacer(modifier = Modifier.height(10.dp))
                val snippet = latestEvent.indication.ifBlank { latestEvent.summary }
                if (snippet.isNotBlank()) {
                    Text(
                        text = snippet,
                        style = MaterialTheme.typography.bodySmall,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(
                        text = "${sourceLabelFor(latestEvent.source)}: ${latestEvent.status}",
                        style = MaterialTheme.typography.labelMedium,
                        color = sourceColorFor(latestEvent.source),
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        text = drug.latestDate,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

@Composable
private fun SettingsDialog(
    currentUrl: String,
    currentToken: String,
    notificationsEnabled: Boolean,
    onlyNewIndications: Boolean,
    onDismiss: () -> Unit,
    onSave: (String, String, Boolean, Boolean) -> Unit,
) {
    var url by remember { mutableStateOf(currentUrl) }
    var token by remember { mutableStateOf(currentToken) }
    var notif by remember { mutableStateOf(notificationsEnabled) }
    var onlyInd by remember { mutableStateOf(onlyNewIndications) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Sync & Notifications") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    label = { Text("Feed JSON URL") },
                    singleLine = false,
                    maxLines = 3,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = token,
                    onValueChange = { token = it },
                    label = { Text("GitHub Token (only if repo is private)") },
                    visualTransformation = PasswordVisualTransformation(),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("Background notifications", modifier = Modifier.weight(1f))
                    Switch(checked = notif, onCheckedChange = { notif = it })
                }
                if (notif) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text("New indications only", modifier = Modifier.weight(1f))
                        Switch(checked = onlyInd, onCheckedChange = { onlyInd = it })
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = { onSave(url, token, notif, onlyInd) }) {
                Text("Save")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        },
    )
}
