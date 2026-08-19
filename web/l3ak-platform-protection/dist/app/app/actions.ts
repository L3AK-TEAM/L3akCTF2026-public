"use server";

export async function meow() {
  const sounds = ["meow", "mrrp", "mreowww"];
  return sounds[Math.floor(Math.random() * sounds.length)];
}
