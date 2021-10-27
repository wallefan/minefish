insert into mods select * from authoritative where true
on conflict (zhash) do
     update set modid=excluded.modid where modid isnull
