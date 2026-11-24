package com.drugtracker.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF0B57D0),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD3E3FD),
    onPrimaryContainer = Color(0xFF041E49),
    secondary = Color(0xFF006A6A),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFCCE8E7),
    background = Color(0xFFF8FAFD),
    surface = Color.White,
    surfaceVariant = Color(0xFFEEF2F8),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFA8C7FA),
    onPrimary = Color(0xFF062E6F),
    primaryContainer = Color(0xFF0842A0),
    onPrimaryContainer = Color(0xFFD3E3FD),
    secondary = Color(0xFF4CDADA),
    onSecondary = Color(0xFF003737),
    background = Color(0xFF101318),
    surface = Color(0xFF181C22),
    surfaceVariant = Color(0xFF232830),
)

object SourceColors {
    val Ema = Color(0xFF1A73E8)       // EU Blue
    val Tlv = Color(0xFF0D9488)       // Teal
    val NtRadet = Color(0xFF7C3AED)   // Purple
    val NewDrug = Color(0xFF16A34A)   // Green
    val NewIndication = Color(0xFFD97706) // Amber
}

@Composable
fun DrugTrackerTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content,
    )
}
