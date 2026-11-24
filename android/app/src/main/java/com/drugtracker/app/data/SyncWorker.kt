package com.drugtracker.app.data

import android.Manifest
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.drugtracker.app.DrugTrackerApp
import com.drugtracker.app.MainActivity

class SyncWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val repo = DrugRepository(applicationContext)
        val result = repo.refreshFromRemote()
        val feed = result.getOrElse { return Result.retry() }

        val previouslySeen = repo.getSeenEventKeys()
        val allKeys = mutableSetOf<String>()
        val newEvents = mutableListOf<Pair<DrugRecord, RegulatoryEvent>>()

        for (drug in feed.drugs) {
            for (event in drug.events) {
                val key = repo.eventKey(drug.id, event)
                allKeys.add(key)
                if (previouslySeen.isNotEmpty() && key !in previouslySeen) {
                    newEvents.add(drug to event)
                }
            }
        }

        repo.markEventsSeen(allKeys)

        if (repo.isNotificationsEnabled() && newEvents.isNotEmpty()) {
            val filtered = if (repo.isNotifyOnlyNewIndications()) {
                newEvents.filter { it.second.updateType == "new_indication" }
            } else {
                newEvents
            }
            if (filtered.isNotEmpty()) {
                postNotification(filtered)
            }
        }

        return Result.success()
    }

    private fun postNotification(items: List<Pair<DrugRecord, RegulatoryEvent>>) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ActivityCompat.checkSelfPermission(
                applicationContext,
                Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        val intent = Intent(applicationContext, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            applicationContext,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val (firstDrug, firstEvent) = items.first()
        val title = if (items.size == 1) {
            "${firstEvent.source}: ${firstDrug.drugName}"
        } else {
            "${items.size} new EMA / TLV / NT-rådet updates"
        }
        val text = if (items.size == 1) {
            "${firstEvent.status} · ${firstEvent.title}"
        } else {
            items.take(3).joinToString(", ") { "${it.first.drugName} (${it.second.source})" }
        }

        val notification = NotificationCompat.Builder(applicationContext, DrugTrackerApp.CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        NotificationManagerCompat.from(applicationContext).notify(1001, notification)
    }
}
