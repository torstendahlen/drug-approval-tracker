package com.drugtracker.app.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.OpenInNew
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.BookmarkBorder
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.drugtracker.app.data.DrugRecord
import com.drugtracker.app.data.RegulatoryEvent
import com.drugtracker.app.ui.theme.SourceColors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DrugDetailSheet(
    drug: DrugRecord,
    isBookmarked: Boolean,
    onToggleBookmark: () -> Unit,
    onDismiss: () -> Unit,
) {
    val context = LocalContext.current

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp)
                .padding(bottom = 32.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = drug.drugName,
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                    )
                    if (drug.activeSubstance.isNotBlank()) {
                        Text(
                            text = drug.activeSubstance,
                            style = MaterialTheme.typography.titleMedium,
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

            Spacer(modifier = Modifier.height(8.dp))

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (drug.atcCode.isNotBlank()) {
                    TagChip(label = "ATC ${drug.atcCode}", color = MaterialTheme.colorScheme.secondary)
                }
                if (drug.therapeuticArea.isNotBlank()) {
                    TagChip(label = drug.therapeuticArea, color = MaterialTheme.colorScheme.primary)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
            HorizontalDivider()
            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "Regulatory Timeline (${drug.events.size})",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Spacer(modifier = Modifier.height(12.dp))

            drug.events.forEach { event ->
                TimelineEventCard(
                    event = event,
                    onOpenUrl = { url ->
                        if (url.isNotBlank()) {
                            runCatching {
                                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                            }
                        }
                    },
                )
                Spacer(modifier = Modifier.height(12.dp))
            }
        }
    }
}

@Composable
private fun TimelineEventCard(
    event: RegulatoryEvent,
    onOpenUrl: (String) -> Unit,
) {
    val sourceColor = sourceColorFor(event.source)
    val sourceLabel = sourceLabelFor(event.source)

    Surface(
        shape = RoundedCornerShape(14.dp),
        tonalElevation = 2.dp,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(sourceColor)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = sourceLabel,
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = sourceColor,
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    UpdateTypeBadge(event.updateType)
                }
                Text(
                    text = event.date,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            if (event.status.isNotBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = event.status,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.SemiBold,
                )
            }

            if (event.indication.isNotBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = event.indication,
                    style = MaterialTheme.typography.bodyMedium,
                )
            } else if (event.summary.isNotBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = event.summary,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }

            if (event.url.isNotBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                TextButton(
                    onClick = { onOpenUrl(event.url) },
                    modifier = Modifier.align(Alignment.End),
                ) {
                    Text("Open official page")
                    Spacer(modifier = Modifier.width(4.dp))
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.OpenInNew,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                    )
                }
            }
        }
    }
}

@Composable
fun TagChip(label: String, color: Color) {
    Surface(
        color = color.copy(alpha = 0.12f),
        shape = RoundedCornerShape(8.dp),
    ) {
        Text(
            text = label,
            color = color,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
        )
    }
}

@Composable
fun UpdateTypeBadge(updateType: String) {
    val (label, color) = when (updateType) {
        "new_indication" -> "New Indication" to SourceColors.NewIndication
        "new_drug" -> "New Drug" to SourceColors.NewDrug
        else -> "Update" to MaterialTheme.colorScheme.secondary
    }
    TagChip(label = label, color = color)
}

fun sourceColorFor(source: String): Color = when (source) {
    "EMA" -> SourceColors.Ema
    "TLV" -> SourceColors.Tlv
    "NT_RADET" -> SourceColors.NtRadet
    else -> Color.Gray
}

fun sourceLabelFor(source: String): String = when (source) {
    "NT_RADET" -> "NT-rådet"
    else -> source
}
