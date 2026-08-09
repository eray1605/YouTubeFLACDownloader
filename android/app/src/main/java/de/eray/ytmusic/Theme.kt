package de.eray.ytmusic

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/**
 * Dieselben Farben wie die Desktop-App (ytmd/config.py), damit beide Fassungen
 * erkennbar dasselbe Programm sind.
 */
object Farben {
    val Akzent = Color(0xFFE94560)         // Überschrift, Suchen-Knopf
    val AkzentHell = Color(0xFFFF6B81)
    val Download = Color(0xFF2ECC71)
    val Playlist = Color(0xFF1DB954)       // Spotify-Grün
    val PlaylistHell = Color(0xFF1ED760)

    val Erfolg = Color(0xFF2ECC71)
    val Info = Color(0xFF3498DB)
    val Warnung = Color(0xFFF39C12)
    val Fehler = Color(0xFFE74C3C)

    // CustomTkinter-Dunkelmodus
    val DunkelHintergrund = Color(0xFF242424)
    val DunkelFlaeche = Color(0xFF2B2B2B)
    val DunkelText = Color(0xFFDCE4EE)
    val DunkelGedaempft = Color(0xFF9A9A9A)

    val HellHintergrund = Color(0xFFEBEBEB)
    val HellFlaeche = Color(0xFFFFFFFF)
    val HellText = Color(0xFF1A1A1A)
    val HellGedaempft = Color(0xFF6E6E6E)
}

private val DunkelSchema = darkColorScheme(
    primary = Farben.Akzent,
    onPrimary = Color.White,
    secondary = Farben.Playlist,
    background = Farben.DunkelHintergrund,
    onBackground = Farben.DunkelText,
    surface = Farben.DunkelFlaeche,
    onSurface = Farben.DunkelText,
    surfaceVariant = Farben.DunkelFlaeche,
    onSurfaceVariant = Farben.DunkelGedaempft,
)

private val HellSchema = lightColorScheme(
    primary = Farben.Akzent,
    onPrimary = Color.White,
    secondary = Farben.Playlist,
    background = Farben.HellHintergrund,
    onBackground = Farben.HellText,
    surface = Farben.HellFlaeche,
    onSurface = Farben.HellText,
    surfaceVariant = Farben.HellFlaeche,
    onSurfaceVariant = Farben.HellGedaempft,
)

@Composable
fun YtmdTheme(dunkel: Boolean, inhalt: @Composable () -> Unit) =
    MaterialTheme(colorScheme = if (dunkel) DunkelSchema else HellSchema, content = inhalt)

/** Statusanzeige je Song – wie STATUS_TEXTS in ytmd/app.py. */
fun statusText(state: String): Pair<String, Color> = when (state) {
    "searching" -> "Suche..." to Farben.Warnung
    "downloading" -> "Lädt..." to Farben.Akzent
    "retrying" -> "Neuer Versuch" to Farben.Warnung
    "done" -> "Fertig" to Farben.Erfolg
    "skipped" -> "Schon da" to Farben.Info
    "failed" -> "Fehler" to Farben.Fehler
    "cancelled" -> "Abgebrochen" to Farben.Warnung
    "no_space" -> "Kein Platz" to Farben.Fehler
    else -> "Wartet" to Farben.DunkelGedaempft
}
