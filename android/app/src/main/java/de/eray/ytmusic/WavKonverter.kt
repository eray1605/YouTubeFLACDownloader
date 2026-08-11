package de.eray.ytmusic

import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Wandelt eine geladene Tonspur auf dem Gerät nach WAV.
 *
 * FFmpeg gibt es auf Android nicht, aber das System bringt eigene Dekoder mit:
 * MediaExtractor liest den Behälter (m4a, webm), MediaCodec entpackt AAC oder
 * Opus zu rohen Abtastwerten, und die schreiben wir mit einem RIFF-Kopf davor
 * als WAV weg. Ein Encoder wird dafür nicht gebraucht – WAV ist unkomprimiert.
 *
 * Für MP3 gibt es auf Android keinen Encoder, das bleibt dem Rechner vorbehalten.
 */
object WavKonverter {

    private const val ZEITLIMIT = 10_000L   // Mikrosekunden je Puffer

    /** True, wenn diese Datei umgewandelt werden kann und sollte. */
    fun kandidat(datei: File): Boolean {
        val endung = datei.extension.lowercase()
        return endung in setOf("m4a", "mp4", "webm", "opus", "ogg", "aac", "mkv")
    }

    /**
     * Wandelt `quelle` nach WAV und gibt die neue Datei zurück – oder null,
     * wenn es nicht geklappt hat. Die Quelldatei wird nur bei Erfolg gelöscht.
     */
    fun nachWav(quelle: File, quelleLoeschen: Boolean = true): File? {
        val ziel = File(quelle.parentFile, quelle.nameWithoutExtension + ".wav")
        if (ziel.exists() && ziel.length() > 44) return ziel

        var extractor: MediaExtractor? = null
        var codec: MediaCodec? = null
        val roh = File(quelle.parentFile, quelle.nameWithoutExtension + ".pcm.tmp")

        try {
            extractor = MediaExtractor().apply { setDataSource(quelle.absolutePath) }
            val spur = (0 until extractor.trackCount).firstOrNull {
                extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)
                    ?.startsWith("audio/") == true
            } ?: return null

            extractor.selectTrack(spur)
            val format = extractor.getTrackFormat(spur)
            val mime = format.getString(MediaFormat.KEY_MIME) ?: return null

            codec = MediaCodec.createDecoderByType(mime)
            codec.configure(format, null, null, 0)
            codec.start()

            var kanaele = format.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
            var rate = format.getInteger(MediaFormat.KEY_SAMPLE_RATE)

            roh.outputStream().use { aus ->
                val info = MediaCodec.BufferInfo()
                var eingabeFertig = false
                var ausgabeFertig = false

                while (!ausgabeFertig) {
                    if (!eingabeFertig) {
                        val i = codec.dequeueInputBuffer(ZEITLIMIT)
                        if (i >= 0) {
                            val puffer = codec.getInputBuffer(i)!!
                            val gelesen = extractor.readSampleData(puffer, 0)
                            if (gelesen < 0) {
                                codec.queueInputBuffer(i, 0, 0, 0,
                                    MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                                eingabeFertig = true
                            } else {
                                codec.queueInputBuffer(i, 0, gelesen,
                                    extractor.sampleTime, 0)
                                extractor.advance()
                            }
                        }
                    }

                    when (val o = codec.dequeueOutputBuffer(info, ZEITLIMIT)) {
                        MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                            val neu = codec.outputFormat
                            kanaele = neu.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
                            rate = neu.getInteger(MediaFormat.KEY_SAMPLE_RATE)
                        }
                        MediaCodec.INFO_TRY_AGAIN_LATER -> { /* warten */ }
                        else -> if (o >= 0) {
                            val puffer = codec.getOutputBuffer(o)!!
                            if (info.size > 0) {
                                val bytes = ByteArray(info.size)
                                puffer.position(info.offset)
                                puffer.get(bytes)
                                aus.write(bytes)
                            }
                            codec.releaseOutputBuffer(o, false)
                            if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) {
                                ausgabeFertig = true
                            }
                        }
                    }
                }
            }

            if (roh.length() <= 0) return null
            wavSchreiben(roh, ziel, kanaele, rate)
            if (quelleLoeschen) quelle.delete()
            return ziel
        } catch (e: Throwable) {
            ziel.delete()
            return null
        } finally {
            try { codec?.stop(); codec?.release() } catch (_: Throwable) {}
            try { extractor?.release() } catch (_: Throwable) {}
            roh.delete()
        }
    }

    /** Rohe Abtastwerte mit RIFF-Kopf als WAV ablegen (16 Bit, Little Endian). */
    private fun wavSchreiben(roh: File, ziel: File, kanaele: Int, rate: Int) {
        val daten = roh.length().toInt()
        val byteProSekunde = rate * kanaele * 2
        val kopf = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
        kopf.put("RIFF".toByteArray())
        kopf.putInt(36 + daten)
        kopf.put("WAVE".toByteArray())
        kopf.put("fmt ".toByteArray())
        kopf.putInt(16)                       // Länge des fmt-Blocks
        kopf.putShort(1)                      // PCM
        kopf.putShort(kanaele.toShort())
        kopf.putInt(rate)
        kopf.putInt(byteProSekunde)
        kopf.putShort((kanaele * 2).toShort())
        kopf.putShort(16)                     // Bit je Abtastwert
        kopf.put("data".toByteArray())
        kopf.putInt(daten)

        RandomAccessFile(ziel, "rw").use { aus ->
            aus.setLength(0)
            aus.write(kopf.array())
            roh.inputStream().use { ein ->
                val puffer = ByteArray(1 shl 16)
                while (true) {
                    val n = ein.read(puffer)
                    if (n <= 0) break
                    aus.write(puffer, 0, n)
                }
            }
        }
    }
}
