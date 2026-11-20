cmake_minimum_required(VERSION 3.20)
project(vls_native CXX C)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# Void Maiz (which itself locates Void Core via its VOIDCORE_ROOT).
set(VOIDMAIZ_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../VoidMaiz" CACHE PATH
    "Path to the Void Maiz repo")
add_subdirectory("${VOIDMAIZ_ROOT}" voidmaiz)

# The UI-free VLS model port: glyph set, port indexing, the starter patch.
add_library(vls_model STATIC src/glyphs.cpp)
target_include_directories(vls_model PUBLIC src)
target_link_libraries(vls_model PUBLIC voidmaiz)

# The shell.
add_executable(vls_native src/app.cpp src/faces.cpp src/style.cpp)
target_link_libraries(vls_native PRIVATE vls_model voidmaiz_view)

if(NOT MSVC)
  # -Wno-missing-field-initializers: the glyph table leans on aggregate
  # defaults on purpose (face/editors/enter stay defaulted per kind).
  target_compile_options(vls_model PRIVATE -Wall -Wextra -Wno-missing-field-initializers)
  target_compile_options(vls_native PRIVATE -Wall -Wextra)
  # Statically link the GCC runtime so the shipped exe is self-contained:
  # only libvoidcore.dll (which sits beside it) stays dynamic. This is what
  # frees the desktop shortcut from the msys64 ucrt64 PATH gotcha — no
  # libstdc++-6.dll / libgcc_s_seh-1.dll shadowing at launch.
  target_link_options(vls_native PRIVATE -static-libgcc -static-libstdc++)
  if(WIN32)
    # Fully static on Windows only. On Linux, libGL and libc are the system's
    # and can only be linked dynamically: `-static` there fails with "attempted
    # static link of dynamic object libGL.so" (Ubuntu 24.04, 2026-11-19).
    target_link_options(vls_native PRIVATE -static)
  endif()
endif()

enable_testing()
add_executable(vls_starter_smoke tests/starter_smoke.cpp)
target_link_libraries(vls_starter_smoke PRIVATE vls_model)
add_test(NAME vls_starter_smoke COMMAND vls_starter_smoke)
