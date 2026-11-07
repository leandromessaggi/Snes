plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "br.com.rom2native"
    compileSdk = 35
    defaultConfig {
        applicationId = "br.com.rom2native"
        minSdk = 26
        targetSdk = 35
        versionCode = 8
        versionName = "0.8-data-driven-missions"
        ndk { abiFilters += listOf("arm64-v8a") }
    }
    ndkVersion = "27.2.12479018"
    externalNativeBuild { cmake { path = file("src/main/cpp/CMakeLists.txt") } }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
    packaging { jniLibs { useLegacyPackaging = true } }
}
