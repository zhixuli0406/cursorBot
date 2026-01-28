package com.cursorbot.node.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.*
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.cursorbot.node.model.CanvasComponent
import com.cursorbot.node.model.CanvasState
import com.cursorbot.node.model.ComponentType
import com.cursorbot.node.viewmodel.MainViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CanvasScreen(viewModel: MainViewModel) {
    val canvasState by viewModel.canvasState.collectAsState()
    val isCanvasActive by viewModel.isCanvasActive.collectAsState()
    val isConnected by viewModel.isConnected.collectAsState()
    
    var scale by remember { mutableFloatStateOf(1f) }
    var offset by remember { mutableStateOf(Offset.Zero) }
    var selectedComponentId by remember { mutableStateOf<String?>(null) }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Canvas") },
                actions = {
                    if (isCanvasActive) {
                        var showMenu by remember { mutableStateOf(false) }
                        
                        IconButton(onClick = { showMenu = true }) {
                            Icon(Icons.Default.Add, contentDescription = "Add Component")
                        }
                        
                        DropdownMenu(
                            expanded = showMenu,
                            onDismissRequest = { showMenu = false }
                        ) {
                            DropdownMenuItem(
                                text = { Text("Add Text") },
                                onClick = {
                                    showMenu = false
                                    // Add text component
                                },
                                leadingIcon = { Icon(Icons.Default.TextFields, null) }
                            )
                            DropdownMenuItem(
                                text = { Text("Add Code") },
                                onClick = {
                                    showMenu = false
                                    // Add code component
                                },
                                leadingIcon = { Icon(Icons.Default.Code, null) }
                            )
                            DropdownMenuItem(
                                text = { Text("Add Image") },
                                onClick = {
                                    showMenu = false
                                    // Add image component
                                },
                                leadingIcon = { Icon(Icons.Default.Image, null) }
                            )
                        }
                        
                        IconButton(onClick = { viewModel.closeCanvas() }) {
                            Icon(Icons.Default.Close, contentDescription = "Close Canvas")
                        }
                    }
                }
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            if (isCanvasActive && canvasState != null) {
                CanvasContent(
                    canvas = canvasState!!,
                    scale = scale,
                    offset = offset,
                    selectedComponentId = selectedComponentId,
                    onScaleChange = { scale = it },
                    onOffsetChange = { offset = it },
                    onComponentSelected = { selectedComponentId = it }
                )
            } else {
                EmptyCanvasView(
                    isConnected = isConnected,
                    onCreateCanvas = { viewModel.createCanvas() }
                )
            }
        }
    }
}

@Composable
private fun EmptyCanvasView(
    isConnected: Boolean,
    onCreateCanvas: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Default.Dashboard,
            contentDescription = null,
            modifier = Modifier.size(80.dp),
            tint = MaterialTheme.colorScheme.outline
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "No Active Canvas",
            style = MaterialTheme.typography.titleMedium
        )
        
        Spacer(modifier = Modifier.height(8.dp))
        
        Text(
            text = "Create a canvas to visualize your work",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.outline
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        Button(
            onClick = onCreateCanvas,
            enabled = isConnected
        ) {
            Icon(Icons.Default.Add, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Create Canvas")
        }
    }
}

@Composable
private fun CanvasContent(
    canvas: CanvasState,
    scale: Float,
    offset: Offset,
    selectedComponentId: String?,
    onScaleChange: (Float) -> Unit,
    onOffsetChange: (Offset) -> Unit,
    onComponentSelected: (String?) -> Unit
) {
    var currentScale by remember { mutableFloatStateOf(scale) }
    var currentOffset by remember { mutableStateOf(offset) }
    
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .pointerInput(Unit) {
                detectTransformGestures { centroid, pan, zoom, rotation ->
                    currentScale = (currentScale * zoom).coerceIn(0.5f, 3f)
                    currentOffset += pan
                    onScaleChange(currentScale)
                    onOffsetChange(currentOffset)
                }
            }
    ) {
        // Canvas background grid
        Canvas(
            modifier = Modifier
                .fillMaxSize()
                .graphicsLayer(
                    scaleX = currentScale,
                    scaleY = currentScale,
                    translationX = currentOffset.x,
                    translationY = currentOffset.y
                )
        ) {
            // Draw grid
            val gridSize = 50f
            val gridColor = Color.Gray.copy(alpha = 0.2f)
            
            for (x in 0..size.width.toInt() step gridSize.toInt()) {
                drawLine(
                    color = gridColor,
                    start = Offset(x.toFloat(), 0f),
                    end = Offset(x.toFloat(), size.height),
                    strokeWidth = 1f
                )
            }
            
            for (y in 0..size.height.toInt() step gridSize.toInt()) {
                drawLine(
                    color = gridColor,
                    start = Offset(0f, y.toFloat()),
                    end = Offset(size.width, y.toFloat()),
                    strokeWidth = 1f
                )
            }
        }
        
        // Canvas components
        canvas.components.forEach { component ->
            CanvasComponentView(
                component = component,
                isSelected = component.id == selectedComponentId,
                scale = currentScale,
                offset = currentOffset,
                onClick = { onComponentSelected(component.id) }
            )
        }
    }
}

@Composable
private fun CanvasComponentView(
    component: CanvasComponent,
    isSelected: Boolean,
    scale: Float,
    offset: Offset,
    onClick: () -> Unit
) {
    val x = (component.x * scale) + offset.x
    val y = (component.y * scale) + offset.y
    val width = component.width * scale
    val height = component.height * scale
    
    Surface(
        modifier = Modifier
            .offset(x = x.dp, y = y.dp)
            .size(width = width.dp, height = height.dp)
            .pointerInput(Unit) {
                detectTapGestures { onClick() }
            },
        shape = MaterialTheme.shapes.medium,
        color = if (isSelected) {
            MaterialTheme.colorScheme.primaryContainer
        } else {
            MaterialTheme.colorScheme.surface
        },
        tonalElevation = 2.dp,
        border = if (isSelected) {
            ButtonDefaults.outlinedButtonBorder
        } else null
    ) {
        when (component.type) {
            ComponentType.TEXT -> TextComponent(component)
            ComponentType.CODE -> CodeComponent(component)
            ComponentType.IMAGE -> ImageComponent(component)
            ComponentType.BUTTON -> ButtonComponent(component)
            ComponentType.INPUT -> InputComponent(component)
            else -> DefaultComponent(component)
        }
    }
}

@Composable
private fun TextComponent(component: CanvasComponent) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(8.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = component.content,
            style = MaterialTheme.typography.bodyMedium
        )
    }
}

@Composable
private fun CodeComponent(component: CanvasComponent) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Color.Black
    ) {
        Text(
            text = component.content,
            modifier = Modifier.padding(8.dp),
            style = MaterialTheme.typography.bodySmall,
            color = Color.Green,
            fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace
        )
    }
}

@Composable
private fun ImageComponent(component: CanvasComponent) {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = Icons.Default.Image,
            contentDescription = null,
            modifier = Modifier.size(48.dp),
            tint = MaterialTheme.colorScheme.outline
        )
    }
}

@Composable
private fun ButtonComponent(component: CanvasComponent) {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Button(onClick = { }) {
            Text(component.content)
        }
    }
}

@Composable
private fun InputComponent(component: CanvasComponent) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(8.dp),
        contentAlignment = Alignment.Center
    ) {
        OutlinedTextField(
            value = "",
            onValueChange = {},
            placeholder = { Text(component.content) },
            modifier = Modifier.fillMaxWidth()
        )
    }
}

@Composable
private fun DefaultComponent(component: CanvasComponent) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(8.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = component.type.name,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.outline
        )
    }
}
