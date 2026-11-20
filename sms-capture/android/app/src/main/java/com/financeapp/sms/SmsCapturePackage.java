package com.financeapp.sms;

import com.facebook.react.ReactPackage;
import com.facebook.react.bridge.NativeModule;
import com.facebook.react.bridge.ReactApplicationContext;
import java.util.Collections;
import java.util.List;

/** Register in MainApplication: PackageList(this).packages.apply { add(SmsCapturePackage()) } */
public class SmsCapturePackage implements ReactPackage {
    @Override
    public List<NativeModule> createNativeModules(ReactApplicationContext context) {
        return Collections.singletonList(new SmsCaptureModule(context));
    }

    // Raw List keeps this compatible with both the older Java and the newer Kotlin ReactPackage signatures.
    @Override
    @SuppressWarnings({"rawtypes", "unchecked"})
    public List createViewManagers(ReactApplicationContext context) {
        return Collections.emptyList();
    }
}
