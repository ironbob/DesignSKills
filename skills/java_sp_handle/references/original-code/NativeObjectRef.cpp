#include "nativeref/NativeObjectRef.h"
#include "autils/stlog.h"
#include "NativeObjectRef.h"

#include <mutex>
#include <map>

namespace anbase {

static anbase::JavaClassJvmData NativeObjectRef_JvmInfo;
static anbase::JavaClassInfo NativeObjectRef_ClassInfo =
    {
        // class name
        "com/arashivision/insbase/nativeref/NativeObjectRef",
        // object fields
        {
            {"mWrapPtr", "J" },
        },
        // static fields
        {
        },
        // object methods
        {
            { "getWrapPtr", "()J" },
            { "moveGetWrapPtr", "()J" },
        },
        // static methods
        {
        },
        // constructors
        {
        },
        &NativeObjectRef_JvmInfo
    };

struct NativeWrap {
    uint32_t typeId;
    std::shared_ptr<void> obj;
};

 bool IsSuchType(JNIEnv *env, jobject obj, uint32_t typeId) {
    CHECK_MSG(obj != nullptr, "native object ref is null, %u", typeId);
    JavaObject caller(&NativeObjectRef_ClassInfo, obj, env);
    NativeWrap *wrap = reinterpret_cast<NativeWrap *>(
            static_cast<intptr_t>(caller.callLongMethod("getWrapPtr")));
    if(wrap == nullptr) {
        return false;
    }
   return wrap->typeId == typeId;
}

static std::shared_ptr<void> RefGet(JNIEnv *env, jobject obj, uint32_t typeId, bool move) {
    CHECK_MSG(obj != nullptr, "native object ref is null, %u", typeId);
    JavaObject caller(&NativeObjectRef_ClassInfo, obj, env);
    NativeWrap *wrap = reinterpret_cast<NativeWrap *>(
                static_cast<intptr_t>(caller.callLongMethod(move ? "moveGetWrapPtr" : "getWrapPtr")));
    if(wrap == nullptr) {
        return nullptr;
    }
    CHECK_MSG(wrap->typeId == typeId, "bad native object ref, type not match! expect: %u, current: %u",
              typeId, wrap->typeId);
    auto ref = wrap->obj;
    if(move) {
        delete wrap;
    }
    return ref;
}

std::shared_ptr<void> _CopyRefGet(JNIEnv *env, jobject obj, uint32_t typeId) {
    return RefGet(env, obj, typeId, false);
}

std::shared_ptr<void> _MoveRefGet(JNIEnv *env, jobject obj, uint32_t typeId) {
    return RefGet(env, obj, typeId, true);
}

void *_PtrGetFromNativeWrap(jlong nativeWrap, uint32_t typeId) {
    if(nativeWrap == 0) {
        return nullptr;
    }
    auto wrap = reinterpret_cast<NativeWrap *>(static_cast<intptr_t>(nativeWrap));
    CHECK_MSG(wrap->typeId == typeId, "bad native object ref, type not match! expect: %u, current: %u",
        typeId, wrap->typeId);
    return wrap->obj.get();
}


NativeWrap *_NewRefWrap(const std::shared_ptr<void> &nativeObj, uint32_t typeId) {
    NativeWrap *wrap = new NativeWrap();
    wrap->typeId = typeId;
    wrap->obj = nativeObj;
    return wrap;
}

std::mutex gCacheMutex;
struct SymbolItem {
    jclass clz;
    jmethodID constructorMid;
};
std::map<std::string, SymbolItem> gCacheSymbols;

LocalJniObject NewJavaNativeObjectRef(JNIEnv *env, NativeWrap *wrap, const std::string &className) {
    std::lock_guard<std::mutex> lock(gCacheMutex);
    if(gCacheSymbols.count(className) <= 0) {
        jclass _clz = FindClass(env, className);
        CHECK_MSG(_clz != nullptr, "NativeObjectRef: can't find class: %s", className.c_str());
        jclass clz = reinterpret_cast<jclass>(env->NewGlobalRef(_clz));
        env->DeleteLocalRef(_clz);
        jmethodID constructorMid = env->GetMethodID(clz, "<init>", "(J)V");
        CHECK_MSG(constructorMid != nullptr, "NativeObjectRef: no required constructor for class: %s", className.c_str());
        gCacheSymbols.insert({className, SymbolItem{clz, constructorMid}});
    }

    SymbolItem symbolItem = gCacheSymbols.at(className);
    jobject _obj = env->NewObject(symbolItem.clz, symbolItem.constructorMid, static_cast<jlong>(reinterpret_cast<intptr_t>(wrap)));
    return LocalJniObject(_obj, env);
}

}

using namespace anbase;

extern "C" JNIEXPORT void JNICALL
Java_com_arashivision_insbase_nativeref_NativeObjectRef_nativeFree(JNIEnv *env, jobject instance) {
    JavaObject caller(&NativeObjectRef_ClassInfo, instance, env);
    NativeWrap *wrap = reinterpret_cast<NativeWrap *>(static_cast<intptr_t>(caller.getLong("mWrapPtr")));
    caller.setLong("mWrapPtr", 0);
    delete wrap;
}


extern "C" JNIEXPORT jboolean JNICALL
Java_com_arashivision_insbase_nativeref_NativeObjectRef_nativeHasSameNativeObject(JNIEnv *env, jobject instance, jobject ref) {
    if(ref == nullptr || instance == nullptr) {
        return JNI_FALSE;
    }
    JavaObject caller(&NativeObjectRef_ClassInfo, instance, env);
    NativeWrap *wrap = reinterpret_cast<NativeWrap *>(static_cast<intptr_t>(caller.getLong("mWrapPtr")));
    JavaObject refCaller(&NativeObjectRef_ClassInfo, ref, env);
    NativeWrap *refWrap = reinterpret_cast<NativeWrap *>(static_cast<intptr_t>(refCaller.getLong("mWrapPtr")));
    std::shared_ptr<void> instanceObj = wrap != nullptr ? wrap->obj : nullptr;
    std::shared_ptr<void> refObj = refWrap != nullptr ? refWrap->obj : nullptr;
    return instanceObj == refObj ? JNI_TRUE : JNI_FALSE;
}
