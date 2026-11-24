package com.drugtracker.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.drugtracker.app.data.SyncWorker
import java.util.concurrent.TimeUnit

class DrugTrackerApp : Application() {

    companion object {
        const val CHANNEL_ID = "drug_updates_channel"
        private const val WORK_NAME = "drug_feed_periodic_sync"
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        scheduleBackgroundSync()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Drug Approvals & Indications",
                NotificationManager.IMPORTANCE_DEFAULT,
            ).apply {
                description = "Notifications for new EMA, TLV, and NT-rådet decisions"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun scheduleBackgroundSync() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val request = PeriodicWorkRequestBuilder<SyncWorker>(12, TimeUnit.HOURS)
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            request,
        )
    }
}
