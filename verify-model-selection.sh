#!/bin/bash
#
# Verification Script for Subtask 1-4: Model Selection Configuration
#
# This script verifies that model selection in the OllamaModelSelector component
# correctly sets the configuration including model name and dimension.
#

set -e

echo "========================================"
echo "Subtask 1-4: Model Selection Verification"
echo "========================================"
echo ""

# Test 1: Verify OllamaModelSelector Component Exists
echo "✓ Test 1: Verify OllamaModelSelector component exists"
if [ -f "apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx" ]; then
    echo "  ✅ OllamaModelSelector.tsx found"
else
    echo "  ❌ OllamaModelSelector.tsx not found"
    exit 1
fi

# Test 2: Verify Recommended Models Configuration
echo ""
echo "✓ Test 2: Verify recommended models have correct dimensions"

# Extract model dimensions from the code
qwen3_4b_dim=$(grep -A 4 "name: 'qwen3-embedding:4b'" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx | grep "dim:" | sed 's/[^0-9]//g')
qwen3_8b_dim=$(grep -A 4 "name: 'qwen3-embedding:8b'" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx | grep "dim:" | sed 's/[^0-9]//g')
qwen3_06b_dim=$(grep -A 4 "name: 'qwen3-embedding:0.6b'" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx | grep "dim:" | sed 's/[^0-9]//g')
gemma_dim=$(grep -A 4 "name: 'embeddinggemma'" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx | grep "dim:" | sed 's/[^0-9]//g')
nomic_dim=$(grep -A 4 "name: 'nomic-embed-text'" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx | grep "dim:" | sed 's/[^0-9]//g')

echo "  Model dimensions extracted from code:"
echo "    - qwen3-embedding:4b (recommended): $qwen3_4b_dim"
echo "    - qwen3-embedding:8b (quality): $qwen3_8b_dim"
echo "    - qwen3-embedding:0.6b (fast): $qwen3_06b_dim"
echo "    - embeddinggemma: $gemma_dim"
echo "    - nomic-embed-text: $nomic_dim"

if [ "$qwen3_4b_dim" = "2560" ] && [ "$qwen3_8b_dim" = "4096" ] && [ "$qwen3_06b_dim" = "1024" ] && [ "$gemma_dim" = "768" ] && [ "$nomic_dim" = "768" ]; then
    echo "  ✅ All model dimensions are correct"
else
    echo "  ❌ Model dimensions are incorrect"
    exit 1
fi

# Test 3: Verify handleSelect Function
echo ""
echo "✓ Test 3: Verify handleSelect function implementation"

# Check if handleSelect calls onModelSelect with model name and dimension
if grep -q "onModelSelect(model.name, model.dim)" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx; then
    echo "  ✅ handleSelect correctly passes model name and dimension to parent"
else
    echo "  ❌ handleSelect does not correctly pass model and dimension"
    exit 1
fi

# Check toggle behavior (deselect when clicking selected model)
if grep -q "if (selectedModel === model.name)" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx && \
   grep -q "onModelSelect('', 0)" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx; then
    echo "  ✅ Toggle behavior implemented (deselect on second click)"
else
    echo "  ❌ Toggle behavior not implemented correctly"
    exit 1
fi

# Check that only installed models can be selected
if grep -q "if (!model.installed || disabled) return;" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx; then
    echo "  ✅ Only installed models can be selected"
else
    echo "  ❌ Selection guard not implemented correctly"
    exit 1
fi

# Test 4: Verify Visual Highlighting
echo ""
echo "✓ Test 4: Verify visual highlighting for selected models"

# Check if isSelected variable is used for styling
if grep -q "const isSelected = selectedModel === model.name" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx && \
   grep -q "isSelected && 'border-primary bg-primary/5'" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx; then
    echo "  ✅ Selected model has visual highlighting (border and background)"
else
    echo "  ❌ Visual highlighting not implemented correctly"
    exit 1
fi

# Check if checkmark icon is shown for selected models
if grep -q "{isSelected && <Check className=\"h-3 w-3\" />}" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx; then
    echo "  ✅ Checkmark icon displayed for selected model"
else
    echo "  ❌ Checkmark icon not displayed correctly"
    exit 1
fi

# Test 5: Verify Dimension Display in UI
echo ""
echo "✓ Test 5: Verify dimension is displayed in the UI"

if grep -q "({model.dim} dim)" apps/frontend/src/renderer/components/onboarding/OllamaModelSelector.tsx; then
    echo "  ✅ Dimension value is displayed next to model name"
else
    echo "  ❌ Dimension value not displayed in UI"
    exit 1
fi

# Test 6: Verify MemoryStep Integration
echo ""
echo "✓ Test 6: Verify MemoryStep integration with OllamaModelSelector"

if [ -f "apps/frontend/src/renderer/components/onboarding/MemoryStep.tsx" ]; then
    echo "  ✅ MemoryStep.tsx found"
else
    echo "  ❌ MemoryStep.tsx not found"
    exit 1
fi

# Check if MemoryStep uses OllamaModelSelector
if grep -q "import { OllamaModelSelector } from './OllamaModelSelector'" apps/frontend/src/renderer/components/onboarding/MemoryStep.tsx; then
    echo "  ✅ MemoryStep imports OllamaModelSelector"
else
    echo "  ❌ MemoryStep does not import OllamaModelSelector"
    exit 1
fi

# Check if onModelSelect callback updates both model and dimension
if grep -q "ollamaEmbeddingModel: model" apps/frontend/src/renderer/components/onboarding/MemoryStep.tsx && \
   grep -q "ollamaEmbeddingDim: dim" apps/frontend/src/renderer/components/onboarding/MemoryStep.tsx; then
    echo "  ✅ onModelSelect updates both model name and dimension in config"
else
    echo "  ❌ onModelSelect does not update config correctly"
    exit 1
fi

# Test 7: Verify Configuration Persistence
echo ""
echo "✓ Test 7: Verify configuration is saved correctly"

# Check if dimension is included in settings save
if grep -q "memoryOllamaEmbeddingDim: config.ollamaEmbeddingDim" apps/frontend/src/renderer/components/onboarding/MemoryStep.tsx; then
    echo "  ✅ Dimension is saved to settings"
else
    echo "  ❌ Dimension is not saved to settings"
    exit 1
fi

# Check if dimension is included in settings store update
if grep -q "memoryOllamaEmbeddingDim: config.ollamaEmbeddingDim || undefined" apps/frontend/src/renderer/components/onboarding/MemoryStep.tsx; then
    echo "  ✅ Dimension is updated in settings store"
else
    echo "  ❌ Dimension is not updated in settings store"
    exit 1
fi

# Test 8: Verify Validation Logic
echo ""
echo "✓ Test 8: Verify form validation allows proceeding"

# Check if isConfigValid checks for Ollama model selection
if grep -q "if (embeddingProvider === 'ollama')" apps/frontend/src/renderer/components/onboarding/MemoryStep.tsx && \
   grep -q "return !!config.ollamaEmbeddingModel.trim()" apps/frontend/src/renderer/components/onboarding/MemoryStep.tsx; then
    echo "  ✅ Validation checks if Ollama model is selected"
else
    echo "  ❌ Validation logic is incorrect"
    exit 1
fi

# Check if Save button is disabled when config is invalid
if grep -q "disabled={isCheckingInfra || !isConfigValid() || isSaving}" apps/frontend/src/renderer/components/onboarding/MemoryStep.tsx; then
    echo "  ✅ Save button is disabled when config is invalid"
else
    echo "  ❌ Save button validation not implemented correctly"
    exit 1
fi

# Summary
echo ""
echo "========================================"
echo "✅ All Verification Tests Passed!"
echo "========================================"
echo ""
echo "Summary:"
echo "  ✅ Model selection highlights clicked model"
echo "  ✅ Dimension value is set correctly (qwen3-embedding:4b = 2560)"
echo "  ✅ Dimension is displayed in UI next to model name"
echo "  ✅ Configuration is saved with correct dimension"
echo "  ✅ User can proceed to next step after selecting model"
echo ""
echo "Manual Verification Steps (to be performed in browser):"
echo "  1. Start the Electron app: npm run dev"
echo "  2. Navigate to onboarding wizard (Memory step)"
echo "  3. Click on 'qwen3-embedding:4b' model"
echo "  4. Verify:"
echo "     - Model has blue border and background highlight"
echo "     - Checkmark appears in the circular indicator"
echo "     - Dimension shows '(2560 dim)' next to model name"
echo "     - 'Save and Continue' button becomes enabled"
echo "  5. Click 'Save and Continue'"
echo "  6. Verify settings are saved successfully"
echo ""
