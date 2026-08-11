package de.eray.ytmusic

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlin.concurrent.thread

/**
 * Führt den Playlist-Lauf im Vordergrunddienst aus.
 *
 * Ein Lauf über tausende Songs dauert Stunden. Ohne Vordergrunddienst mit
 * sichtbarer Benachrichtigung beendet Android die App, sobald der Bildschirm
 * aus ist.
 */
class DownloadService : Service() {

    /** Wird aus Python heraus aufgerufen (siehe ytmd.headless.run_for_listener). */
    class Listener(private val onEvent: (Int, Int, String) -> Unit) {
        fun onStatus(index: Int, state: String, detail: String?) {
            Fortschritt.zustaende[index] = state
            Fortschritt.letzterSong = "${index + 1}: $state" + (detail?.let { " ($it)" } ?: "")
        }
        fun onProgress(done: Int, total: Int) {
            Fortschritt.fertig = done
            Fortschritt.gesamt = total
            onEvent(done, total, Fortschritt.letzterSong)
        }
    }

    /** Gemeinsamer Zustand, den die Oberfläche ablesen kann. */
    object Fortschritt {
        @Volatile var laeuft = false
        @Volatile var fertig = 0
        @Volatile var gesamt = 0
        @Volatile var letzterSong = ""
        @Volatile var ergebnis: String? = null
        /** Zustand je Songposition – die Worker schreiben nebenläufig hinein. */
        val zustaende = java.util.concurrent.ConcurrentHashMap<Int, String>()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent == null) return START_NOT_STICKY
        val einzelUrl = intent.getStringExtra("url")          // Einzeldownload
        val playlist = intent.getStringExtra("playlist")      // ganze Playlist
        if (einzelUrl == null && playlist == null) return START_NOT_STICKY
        val ziel = intent.getStringExtra("ziel") ?: filesDir.absolutePath
        val format = intent.getStringExtra("format") ?: "wav"
        val workers = intent.getIntExtra("workers", 2)

        kanalAnlegen()
        startForeground(1, benachrichtigung("Wird vorbereitet …"))

        Fortschritt.laeuft = true
        Fortschritt.ergebnis = null
        Fortschritt.zustaende.clear()

        thread(name = "ytmd-lauf") {
            try {
                if (!Python.isStarted()) Python.start(AndroidPlatform(this))
                val py = Python.getInstance()
                val headless: PyObject = py.getModule("ytmd.headless")

                val ergebnis = if (einzelUrl != null) {
                    aktualisieren("Einzelner Song …")
                    headless.callAttr("einzeln_laden", einzelUrl, ziel, format)
                } else {
                    val listener = Listener { done, total, song ->
                        aktualisieren("$done/$total  ·  $song")
                    }
                    headless.callAttr("run_for_listener",
                                      playlist, ziel, format, workers, listener)
                }
                Fortschritt.ergebnis = ergebnis.toString()
            } catch (e: Throwable) {
                Fortschritt.ergebnis = "Fehler: ${e.message}"
            } finally {
                medienIndexAktualisieren(ziel)
                Fortschritt.laeuft = false
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
        return START_STICKY
    }

    /**
     * Neue Dateien beim Medienindex anmelden. Ohne das liegen die Songs zwar im
     * Musikordner, tauchen aber in keiner Musik-App auf, bis Android irgendwann
     * von selbst nachsieht.
     */
    private fun medienIndexAktualisieren(ordner: String) {
        val dateien = java.io.File(ordner).walkTopDown()
            .filter { it.isFile && !it.name.endsWith(".part") }
            .map { it.absolutePath }.toList().toTypedArray()
        if (dateien.isEmpty()) return
        android.media.MediaScannerConnection.scanFile(this, dateien, null, null)
    }

    private fun kanalAnlegen() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val kanal = NotificationChannel(
                KANAL, "Downloads", NotificationManager.IMPORTANCE_LOW)
            (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager)
                .createNotificationChannel(kanal)
        }
    }

    private fun benachrichtigung(text: String) =
        NotificationCompat.Builder(this, KANAL)
            .setContentTitle("Playlist wird geladen")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setOngoing(true)
            .build()

    private fun aktualisieren(text: String) {
        (getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager)
            .notify(1, benachrichtigung(text))
    }

    companion object {
        private const val KANAL = "downloads"
    }
}
