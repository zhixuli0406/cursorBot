package com.cursorbot.node.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.cursorbot.node.ui.screens.*
import com.cursorbot.node.viewmodel.MainViewModel

sealed class Screen(val route: String, val title: String) {
    object Chat : Screen("chat", "Chat")
    object Canvas : Screen("canvas", "Canvas")
    object Camera : Screen("camera", "Camera")
    object Settings : Screen("settings", "Settings")
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CursorBotNavHost(
    navController: NavHostController = rememberNavController(),
    viewModel: MainViewModel = hiltViewModel()
) {
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route
    
    val connectionStatus by viewModel.connectionStatus.collectAsState()
    
    Scaffold(
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Chat, contentDescription = "Chat") },
                    label = { Text("Chat") },
                    selected = currentRoute == Screen.Chat.route,
                    onClick = { navController.navigate(Screen.Chat.route) }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Dashboard, contentDescription = "Canvas") },
                    label = { Text("Canvas") },
                    selected = currentRoute == Screen.Canvas.route,
                    onClick = { navController.navigate(Screen.Canvas.route) }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.CameraAlt, contentDescription = "Camera") },
                    label = { Text("Camera") },
                    selected = currentRoute == Screen.Camera.route,
                    onClick = { navController.navigate(Screen.Camera.route) }
                )
                NavigationBarItem(
                    icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                    label = { Text("Settings") },
                    selected = currentRoute == Screen.Settings.route,
                    onClick = { navController.navigate(Screen.Settings.route) }
                )
            }
        }
    ) { paddingValues ->
        NavHost(
            navController = navController,
            startDestination = Screen.Chat.route,
            modifier = Modifier.padding(paddingValues)
        ) {
            composable(Screen.Chat.route) {
                ChatScreen(viewModel = viewModel)
            }
            composable(Screen.Canvas.route) {
                CanvasScreen(viewModel = viewModel)
            }
            composable(Screen.Camera.route) {
                CameraScreen(viewModel = viewModel)
            }
            composable(Screen.Settings.route) {
                SettingsScreen(viewModel = viewModel)
            }
        }
    }
}
