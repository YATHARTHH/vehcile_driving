#!/usr/bin/env python3
"""
Train Enhanced ML Model
=======================
Script to train the enhanced ML model with all 14 features and predictive maintenance.
Run this to upgrade from the 6-feature model to the 14-feature enhanced model.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ml_model.enhanced_model import main as train_enhanced_model

if __name__ == "__main__":
    print("🚀 Training Enhanced Vehicle ML Model")
    print("=" * 50)
    print("This will create an enhanced model with:")
    print("✅ All 14 collected features (vs 6 in original)")
    print("✅ Predictive maintenance capabilities")
    print("✅ Component-specific wear prediction")
    print("✅ Enhanced behavior classification")
    print()
    
    try:
        # Train the enhanced model
        ml_system = train_enhanced_model()
        
        if ml_system:
            print("\n🎉 SUCCESS! Enhanced ML model trained and saved.")
            print("\nNext steps:")
            print("1. Restart your Flask application")
            print("2. The enhanced model will be automatically loaded")
            print("3. Trip details will show enhanced predictions")
            print("4. Maintenance predictions will be available")
            
        else:
            print("\n❌ Training failed. Check the logs above.")
            
    except Exception as e:
        print(f"\n❌ Error during training: {str(e)}")
        print("Make sure you have sufficient trip data in your database.")